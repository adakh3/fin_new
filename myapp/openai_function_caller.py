from openai import OpenAI
from django.conf import settings
from .quickbooks.quickbooks_integrator import QuickbooksIntegrator
from .quickbooks.quickbooks_auth import QuickbooksAuth
import json
import inspect
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize client as None, will be created when needed
client = None

def get_openai_client():
    global client
    if client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return client

'''this class is used to call OpenAI functions and handle the tool calls from the AI, and also to process the user's message'''

class OpenAIFunctionCaller:
    def __init__(self, user, aiModel, prompt_file_path):

        with open(prompt_file_path, 'r') as file: 
            self.prompt = file.read()
        self.user = user
        self.aiModel = aiModel
        self.qb_auth = QuickbooksAuth(user)
        self.qb_integrator = QuickbooksIntegrator(self.qb_auth)
        self.conversation_history = [
            {"role": "system", "content": f"{self.prompt}\nCurrent date and time: {datetime.now()}"}
        ]


    def get_integrator_functions(self):
        '''
        Returns the functions that the OpenAI model can call
        '''
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_report",
                    "description": "Retrieve financial reports from QuickBooks",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "report_type": {
                                "type": "string",
                                "enum": ["ProfitAndLoss", "BalanceSheet", "CashFlow"],
                                "description": "Type of financial report to retrieve"
                            },
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Start date for the report (YYYY-MM-DD)"
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": "End date for the report (YYYY-MM-DD)"
                            },
                            "accounting_method": {
                                "type": "string",
                                "enum": ["Cash", "Accrual"],
                                "description": "Accounting method to use for the report"
                            },
                            "summarize_column_by": {
                                "type": "string",
                                "enum": ["Month", "Quarter", "Year"],
                                "description": "How to summarize the report columns"
                            }
                        },
                        "required": ["report_type", "start_date", "end_date", "accounting_method"]
                    }
                }
            }
        ]

    '''
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
    '''

    def process_message(self, new_message, prompt_file_path):
        """
        Processes user messages through OpenAI to interact with QuickBooks data.
        
        1. Sends message to OpenAI with available QuickBooks functions
        2. If function needed: executes QB call, gets data, returns analyzed insights
        3. If no function: returns direct AI response
        
        Args:
            new_message (str): User message
            prompt_file_path (str): Analysis prompt file path
        
        Returns:
            str: AI response or financial insights
        """
        with open(prompt_file_path, 'r') as file: 
            prompt = file.read()
        # If the message is empty, return a default response
        if not new_message:
            return "I'm sorry, I couldn't determine the appropriate action. Could you please provide more details or clarify your request?"

        self.conversation_history.append({"role": "user", "content": new_message})

        # Call OpenAI with the conversation history, tools, and tool choice
        response = get_openai_client().chat.completions.create(
            model=self.aiModel,
            messages=self.conversation_history,
            tools=self.get_integrator_functions(),
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message

        # If the response contains tool calls, handle them
        if response_message.tool_calls:
            function_response = self.handle_tool_calls(response_message.tool_calls)
            self.conversation_history.append({"role": "assistant", "content": function_response})

            # Send the function response to OpenAI for summarization
            summary_response = get_openai_client().chat.completions.create(
                model=self.aiModel,
                messages=[
                    {"role": "user", "content": f"{prompt} {function_response}"}
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
        '''
        Handles tool calls from the OpenAI response.
        Executes the requested QuickBooks function and returns the result.
        '''
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