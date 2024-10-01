from openai import OpenAI
from django.conf import settings
from .quickbooks.quickbooks_integrator import QuickbooksIntegrator
from .quickbooks.quickbooks_auth import QuickbooksAuth
import json
import inspect
import os

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class OpenAIFunctionCaller:
    def __init__(self, user, aiModel):
        self.user = user
        self.aiModel = aiModel
        self.qb_auth = QuickbooksAuth(user)
        self.qb_integrator = QuickbooksIntegrator(self.qb_auth)
        self.conversation_history = []

    def get_integrator_functions(self):
        tools = []
        # Define known parameter constraints
        param_constraints = {
            'report_type': {
                "type": "string",
                "enum": ["ProfitAndLoss", "BalanceSheet", "CashFlow"],
                "description": "Type of financial report to retrieve"
            },
            'start_date': {
                "type": "string",
                "format": "date",
                "description": "Start date for the report (YYYY-MM-DD)"
            },
            'end_date': {
                "type": "string",
                "format": "date",
                "description": "End date for the report (YYYY-MM-DD)"
            },
            'accounting_method': {
                "type": "string",
                "enum": ["Cash", "Accrual"],
                "description": "Accounting method to use for the report"
            },
            'summarize_column_by': {
                "type": "string",
                "enum": ["Month", "Quarter", "Year"],
                "description": "How to summarize the report columns"
            },
            'minorversion': {
                "type": "integer",
                "enum": [62],  # or whatever versions you support
                "description": "Minor version of the QuickBooks API to use"
            }
        }

        for name, method in inspect.getmembers(self.qb_integrator, inspect.ismethod):
            if not name.startswith('_'):  # Exclude private methods
                sig = inspect.signature(method)
                parameters = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False
                }
                
                for param, param_sig in sig.parameters.items():
                    if param != 'self':
                        if param in param_constraints:
                            param_info = param_constraints[param]
                        else:
                            param_info = {
                                "type": "string",
                                "description": f"Parameter {param}"
                            }
                        
                        parameters["properties"][param] = param_info
                        parameters["required"].append(param)
                
                tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": method.__doc__ or f"Call the {name} function",
                        "parameters": parameters
                    }
                })
        return tools

    def process_message(self, new_message):
        if not new_message:
            return "I'm sorry, I couldn't determine the appropriate action. Could you please provide more details or clarify your request?"

        self.conversation_history.append({"role": "user", "content": new_message})

        response = client.chat.completions.create(
            model=self.aiModel,
            messages=self.conversation_history,
            tools=self.get_integrator_functions(),
            tool_choice="auto"
        )
        response_message = response.choices[0].message

        if response_message.tool_calls:
            function_response = self.handle_tool_calls(response_message.tool_calls)
            self.conversation_history.append({"role": "assistant", "content": function_response})

            # Send the function response to OpenAI for summarization
            summary_response = client.chat.completions.create(
                model=self.aiModel,
                messages=[
                    {"role": "user", "content": f"Very briefly summarize the 5 most imporant points for the following financial report, mention the report name and dates as well: {function_response}"}
                ]
            )
            summary_message = summary_response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": summary_message})
            return summary_message

        if response_message.content:
            self.conversation_history.append({"role": "assistant", "content": response_message.content})
            return response_message.content

        return "I'm sorry, I couldn't determine the appropriate action. Could you please provide more details or clarify your request?"

    def handle_tool_calls(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if hasattr(self.qb_integrator, function_name):
                try:
                    self.qb_auth.ensure_valid_token()
                    method = getattr(self.qb_integrator, function_name)
                    result = method(**function_args)
                    results.append(f"Result of {function_name}: {result}")
                except Exception as e:
                    results.append(f"An error occurred while calling {function_name}: {str(e)}")
            else:
                results.append(f"Function {function_name} not found in QuickbooksIntegrator")
        
        return "\n".join(results)