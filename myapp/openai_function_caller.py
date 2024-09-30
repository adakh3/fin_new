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
        # Check if the new message is empty. If so, return a message asking for more details.
        if not new_message:
            return "I'm sorry, I couldn't determine the appropriate action. Could you please provide more details or clarify your request?"
        else:
            # Add the new user message to the conversation history
            self.conversation_history.append({"role": "user", "content": new_message})
        # Retrieve the list of available integrator functions
        tools = self.get_integrator_functions()
        # Add the new user message to the conversation history (this line is redundant and can be removed)
        self.conversation_history.append({"role": "user", "content": new_message})
        # Use the OpenAI client to generate a response based on the conversation history and available tools
        response = client.chat.completions.create(
            model=self.aiModel,
            messages=self.conversation_history,
            tools=tools,
            tool_choice="auto"
        )

        # Extract the response message from the OpenAI response
        response_message = response.choices[0].message

        # Add the AI's response to the conversation history
        self.conversation_history.append({"role": "assistant", "content": response_message.content})

        # Check if the AI's response includes any tool calls
        if response_message.tool_calls:
            results = []
            # Iterate through each tool call in the response
            for tool_call in response_message.tool_calls:
                # Extract the function name and arguments from the tool call
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
            if hasattr(self.qb_integrator, function_name):
                try:
                    # Check and refresh token if necessary before making the API call
                    if not self.qb_auth.is_access_token_valid():
                        if not self.qb_auth.refresh_tokens():
                            raise Exception("Failed to refresh QuickBooks tokens")
                        # Re-initialize the QuickBooks client with the new token
                        self.qb_integrator.client = self.qb_integrator.get_client()

                    method = getattr(self.qb_integrator, function_name)
                    result = method(**function_args)
                    results.append(f"Result of {function_name}: {result}")
                except Exception as e:
                    results.append(f"An error occurred while calling {function_name}: {str(e)}")
            else:
                results.append(f"Function {function_name} not found in QuickbooksIntegrator")

            
            # If there are any results from the function calls, add them to the conversation history and return them
            if results:
                function_response = "\n".join(results)
                self.conversation_history.append({"role": "function", "content": function_response})
                return function_response
        
        # If no function was called or if we don't have results, return the AI's response
        if response_message.content:
            return response_message.content
        else:
            return "I'm sorry, I couldn't determine the appropriate action. Could you please provide more details or clarify your request?"