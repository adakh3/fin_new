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
        for name, method in inspect.getmembers(self.qb_integrator, inspect.ismethod):
            if not name.startswith('_'):  # Exclude private methods
                sig = inspect.signature(method)
                tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": method.__doc__ or f"Call the {name} function",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                param: {"type": "string", "description": f"Parameter {param}"}
                                for param in sig.parameters if param != 'self'
                            },
                            "required": [param for param in sig.parameters if param != 'self']
                        }
                    }
                })
        return tools

    def process_message(self, new_message):
        tools = self.get_integrator_functions()
        # Add the new user message to the conversation history
        self.conversation_history.append({"role": "user", "content": new_message})
        response = client.chat.completions.create(
            model=self.aiModel,
            messages=self.conversation_history,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        # Add the AI's response to the conversation history
        self.conversation_history.append({"role": "assistant", "content": response_message.content})

        if response_message.tool_calls:
            results = []
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if hasattr(self.qb_integrator, function_name):
                    method = getattr(self.qb_integrator, function_name)
                    try:
                        result = method(**function_args)
                        results.append(f"Result of {function_name}: {result}")
                    except Exception as e:
                        results.append(f"An error occurred while calling {function_name}: {str(e)}")
                else:
                    results.append(f"Function {function_name} not found in QuickbooksIntegrator")
            
            # If we have results from function calls, add them to the conversation history
            if results:
                function_response = "\n".join(results)
                self.conversation_history.append({"role": "function", "content": function_response})
                return function_response
        
        # If no function was called or if we don't have results, return the AI's response
        if response_message.content:
            return response_message.content
        else:
            return "I'm sorry, I couldn't determine the appropriate action. Could you please provide more details or clarify your request?"