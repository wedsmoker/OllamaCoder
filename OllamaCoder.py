import tkinter as tk
from tkinter import filedialog
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import os # Added for file cleanup

from utils.ollama_api import fetch_ollama_models, query_single_model
from utils.code_execution import execute_code_task
from utils.file_operations import save_script_function, load_script_function

class OllamaMultiModelGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Pthon Assistant")
        self.root.geometry("1000x800") # Increased width for new elements
        
        # Default values
        self.default_system_message = "You are a helpful coding assistant specializing in Python. You can generate code snippets, explain them, and provide examples. You always adhere to Python best practices and conventions. You are friendly and approachable, and will be helpful to users. If the user requests code, you should provide it in a clear and concise manner. If the user asks for explanations, you should provide them in a way that is easy for a novice programmer to understand. You should also provide examples and test cases to help the user verify the code. If the user asks for code that violates Python best practices, you should politely suggest improvements. If the user asks a question about a specific aspect of Python or coding in general, you should provide a helpful and informative answer."
        self.default_context = ""
        self.default_question = "write a simple python script"
        self.default_temperature = 0
        self.default_max_tokens = 4096
        self.ollama_url = "http://localhost:11434"
        self.chat_history = [] # To store prompts and responses
        self.available_models = [] # To store models fetched from Ollama
        self.stop_event = threading.Event() # Event to signal stopping generation
        self.stop_code_event = threading.Event() # Event to signal stopping code execution
        self.current_code_process = None # To hold the subprocess for code execution
        self.code_input_queue = queue.Queue() # Queue for sending input to the running code
        self.code_input_var = tk.StringVar() # Variable for the code input entry
        
        self.create_widgets()
        self._fetch_ollama_models() # Fetch models on startup
        
    def create_widgets(self):
        # Create notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Input Frame
        input_frame = ttk.Frame(notebook)
        notebook.add(input_frame, text="Input Parameters")
        
        # Model Selection (Combobox)
        ttk.Label(input_frame, text="Select Model:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_combobox = ttk.Combobox(input_frame, width=77, state="readonly")
        self.model_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.model_combobox.set("Loading models...") # Initial text
        self.refresh_models_button = ttk.Button(input_frame, text="Refresh Models", command=self._fetch_ollama_models)
        self.refresh_models_button.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # System Message
        ttk.Label(input_frame, text="System Message:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
        self.system_message_text = scrolledtext.ScrolledText(input_frame, width=80, height=5)
        self.system_message_text.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.system_message_text.insert(tk.INSERT, self.default_system_message)
        
        # Context Label and Clear Button
        context_label_frame = ttk.Frame(input_frame)
        context_label_frame.grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        ttk.Label(context_label_frame, text="Context:").pack(side=tk.LEFT)
        self.clear_context_button = ttk.Button(context_label_frame, text="Clear Context", command=self.clear_context)
        self.clear_context_button.pack(side=tk.LEFT, padx=(10, 0))

        self.context_text = scrolledtext.ScrolledText(input_frame, width=80, height=10)
        self.context_text.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.context_text.insert(tk.INSERT, self.default_context)
        
        # Question
        ttk.Label(input_frame, text="Question:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        self.question_text = scrolledtext.ScrolledText(input_frame, width=80, height=3)
        self.question_text.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        self.question_text.insert(tk.INSERT, self.default_question)
        
        # Parameters
        ttk.Label(input_frame, text="Temperature (0-1):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.temperature_entry = ttk.Entry(input_frame, width=10)
        self.temperature_entry.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        self.temperature_entry.insert(0, str(self.default_temperature))
        
        ttk.Label(input_frame, text="Max Tokens:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_tokens_entry = ttk.Entry(input_frame, width=10)
        self.max_tokens_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        self.max_tokens_entry.insert(0, str(self.default_max_tokens))
        
        ttk.Label(input_frame, text="Ollama URL:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        self.ollama_url_entry = ttk.Entry(input_frame, width=80)
        self.ollama_url_entry.grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        self.ollama_url_entry.insert(0, self.ollama_url)
        
        # Submit and Stop Buttons
        self.submit_button = ttk.Button(input_frame, text="Query Model", command=self.query_model_threaded)
        self.submit_button.grid(row=7, column=1, sticky=tk.E, padx=5, pady=10)
        self.stop_button = ttk.Button(input_frame, text="Stop Generation", command=self.stop_generation, state=tk.DISABLED)
        self.stop_button.grid(row=7, column=0, sticky=tk.W, padx=5, pady=10)
        
        # Results Frame
        self.results_frame = ttk.Frame(notebook)
        notebook.add(self.results_frame, text="Results")
        
        # Results Text
        self.results_text = scrolledtext.ScrolledText(self.results_frame, width=110, height=20) # Reduced height
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Chat History Frame
        self.chat_history_frame = ttk.Frame(notebook)
        notebook.add(self.chat_history_frame, text="Chat History")

        self.chat_history_text = scrolledtext.ScrolledText(self.chat_history_frame, width=110, height=40)
        self.chat_history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.chat_history_text.config(state=tk.DISABLED) # Make it read-only

        # Generated Code Frame
        self.generated_code_frame = ttk.Frame(notebook)
        notebook.add(self.generated_code_frame, text="Generated Code")

        # Frame for code text and run/edit buttons
        code_controls_frame = ttk.Frame(self.generated_code_frame)
        code_controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(code_controls_frame, text="Generated Python Code:").pack(side=tk.LEFT)
        self.run_code_button = ttk.Button(code_controls_frame, text="Run Code", command=self.run_generated_code)
        self.run_code_button.pack(side=tk.RIGHT)
        self.stop_code_button = ttk.Button(code_controls_frame, text="Stop Code", command=self.stop_code_execution, state=tk.DISABLED)
        self.stop_code_button.pack(side=tk.RIGHT, padx=(5, 0))
        self.edit_code_button = ttk.Button(code_controls_frame, text="Edit Code", command=self.enable_code_editing)
        self.edit_code_button.pack(side=tk.RIGHT, padx=(5, 0))
        self.save_code_button = ttk.Button(code_controls_frame, text="Save Code", command=lambda: save_script_function(self))
        self.save_code_button.pack(side=tk.RIGHT, padx=(5, 0))
        self.load_code_button = ttk.Button(code_controls_frame, text="Load Code", command=lambda: load_script_function(self))
        self.load_code_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.generated_code_text = scrolledtext.ScrolledText(self.generated_code_frame, width=110, height=20)
        self.generated_code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.generated_code_text.config(state=tk.DISABLED) # Make it read-only

        # Output for generated code execution
        ttk.Label(self.generated_code_frame, text="Code Execution Output:").pack(fill=tk.X, padx=5, pady=5)
        self.code_output_text = scrolledtext.ScrolledText(self.generated_code_frame, width=110, height=10)
        self.code_output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.code_output_text.config(state=tk.DISABLED) # Make it read-only

        # Input for generated code execution
        code_input_frame = ttk.Frame(self.generated_code_frame)
        code_input_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(code_input_frame, text="Input to Code:").pack(side=tk.LEFT)
        self.code_input_entry = ttk.Entry(code_input_frame, textvariable=self.code_input_var, width=80, state=tk.DISABLED)
        self.code_input_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        self.send_code_input_button = ttk.Button(code_input_frame, text="Send Input", command=self.send_code_input, state=tk.DISABLED)
        self.send_code_input_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)

    def _fetch_ollama_models(self):
        """Fetches available models from the Ollama API and populates the combobox."""
        fetch_ollama_models(self)
    
    def get_input_values(self):
        """Get all input values from the GUI"""
        try:
            model = self.model_combobox.get()
            if not model or model == "Loading models..." or model == "No models found." or model == "Ollama server not reachable.":
                messagebox.showerror("Input Error", "Please select a valid Ollama model.")
                return None

            system_message = self.system_message_text.get("1.0", tk.END).strip()
            context = self.context_text.get("1.0", tk.END).strip() # Get current context from GUI
            question = self.question_text.get("1.0", tk.END).strip()
            temperature = float(self.temperature_entry.get())
            max_tokens = int(self.max_tokens_entry.get())
            ollama_url = self.ollama_url_entry.get().strip()
            
            return {
                "model": model,
                "system_message": system_message,
                "context": context,
                "question": question,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "ollama_url": ollama_url
            }
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input value: {str(e)}")
            return None
    
    def query_model_threaded(self):
        """Starts the model query in a separate thread to keep GUI responsive."""
        inputs = self.get_input_values()
        if inputs is None:
            return
        
        self.stop_event.clear() # Clear the stop event for a new query
        self.submit_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL) # Enable stop button
        self.run_code_button.config(state=tk.DISABLED) # Disable run button during query
        self.edit_code_button.config(state=tk.DISABLED) # Disable edit button during query
        self.code_input_entry.config(state=tk.DISABLED) # Disable code input during query
        self.send_code_input_button.config(state=tk.DISABLED) # Disable send input button during query
        self.status_var.set("Querying model...")
        self.root.update()
        
        # Clear previous results and generated code
        self.results_text.delete("1.0", tk.END)
        self.generated_code_text.config(state=tk.NORMAL)
        self.generated_code_text.delete("1.0", tk.END)
        self.generated_code_text.config(state=tk.DISABLED)
        self.code_output_text.config(state=tk.NORMAL)
        self.code_output_text.delete("1.0", tk.END)
        self.code_output_text.config(state=tk.DISABLED)

        # Start the query in a new thread
        threading.Thread(target=self._query_model_task, args=(inputs,)).start()

    def stop_generation(self):
        """Sets the stop event to signal the generation process to stop."""
        self.stop_event.set()
        self.status_var.set("Stopping generation...")
        self.stop_button.config(state=tk.DISABLED)
        self.submit_button.config(state=tk.NORMAL)
        self.root.update_idletasks()

    def enable_code_editing(self):
        """Enables editing of the generated code text area."""
        self.generated_code_text.config(state=tk.NORMAL)
        self.status_var.set("Generated code is now editable.")
        messagebox.showinfo("Edit Code", "You can now edit the generated code. Click 'Run Code' to execute your modified code.")

    def stop_code_execution(self):
        """Sets the stop event to signal the code execution process to stop."""
        self.stop_code_event.set()
        if self.current_code_process and self.current_code_process.poll() is None:
            print("Stop code execution event detected. Terminating process.")
            self.current_code_process.terminate() # Send SIGTERM
            try:
                self.current_code_process.wait(timeout=5) # Wait for process to terminate
            except subprocess.TimeoutExpired:
                if self.current_code_process.poll() is None: # If still running, force kill
                    self.current_code_process.kill() # Send SIGKILL
        self.status_var.set("Stopping code execution...")
        self.stop_code_button.config(state=tk.DISABLED)
        self.run_code_button.config(state=tk.NORMAL)
        self.code_input_entry.config(state=tk.DISABLED) # Disable code input
        self.send_code_input_button.config(state=tk.DISABLED) # Disable send input button
        self.root.update_idletasks()

    def clear_context(self):
        """Clears the context text area and resets it to the default context, and clears chat history."""
        self.context_text.delete("1.0", tk.END)
        self.context_text.insert(tk.INSERT, self.default_context)
        self.chat_history = [] # Clear the chat history list
        self.chat_history_text.config(state=tk.NORMAL)
        self.chat_history_text.delete("1.0", tk.END) # Clear the chat history display
        self.chat_history_text.config(state=tk.DISABLED)
        self.status_var.set("Context and chat history cleared.")
        messagebox.showinfo("Context Cleared", "The context input field and chat history have been reset to their default values.")

    def send_code_input(self):
        """Sends the content of the code input entry to the running subprocess."""
        input_text = self.code_input_var.get()
        if input_text:
            self.code_input_queue.put(input_text + "\n") # Add newline for input()
            self.code_input_var.set("") # Clear the input entry
            self.code_output_text.config(state=tk.NORMAL)
            self.code_output_text.insert(tk.END, f"> {input_text}\n") # Show user's input in output
            self.code_output_text.see(tk.END)
            self.code_output_text.config(state=tk.DISABLED)
            self.root.update_idletasks()
            
            # Attempt to write to stdin immediately if process is running
            if self.current_code_process and self.current_code_process.stdin:
                try:
                    # Get the input from the queue (it should be there from the put call above)
                    input_to_send = self.code_input_queue.get_nowait()
                    self.current_code_process.stdin.write(input_to_send)
                    self.current_code_process.stdin.flush()
                    print(f"Sent input to subprocess: {input_to_send.strip()}") # Debugging log
                except queue.Empty:
                    pass # Should not happen
                except BrokenPipeError:
                    print("BrokenPipeError: Subprocess stdin pipe is closed. Process might have exited.")
                except Exception as e:
                    print(f"Error sending input to subprocess: {e}")
        else:
            messagebox.showwarning("Empty Input", "Please enter some text to send as input.")

    def _query_model_task(self, inputs):
        """Task to query a single model and update GUI."""
        try:
            model = inputs["model"]
            self.results_text.insert(tk.END, f"\n=== Querying {model} ===\n")
            self.root.update()
            
            response_content = query_single_model(
                self,
                model=model,
                system_message=inputs["system_message"],
                context=inputs["context"], # Use the current content of the context_text
                question=inputs["question"],
                temperature=inputs["temperature"],
                max_tokens=inputs["max_tokens"],
                ollama_url=inputs["ollama_url"]
            )
            
            if not self.stop_event.is_set(): # Only update if not stopped
                self.results_text.insert(tk.END, f"\nResponse from {model}:\n")
                self.results_text.insert(tk.END, response_content)
                self.results_text.insert(tk.END, "\n" + "="*50 + "\n")
                self.results_text.see(tk.END)
                self.root.update()

                # Store in chat history (without generated code in history entry itself)
                self._add_to_chat_history(inputs["question"], response_content)

                # Attempt to generate Python code
                generated_code = self._extract_python_code(response_content)
                if generated_code:
                    self.generated_code_text.config(state=tk.NORMAL)
                    self.generated_code_text.delete("1.0", tk.END) # Clear previous code
                    self.generated_code_text.insert(tk.END, generated_code)
                    self.generated_code_text.config(state=tk.DISABLED)
                    self.generated_code_text.see(tk.END)
                    self.run_code_button.config(state=tk.NORMAL) # Enable run button
                    self.edit_code_button.config(state=tk.NORMAL) # Enable edit button
                    self.root.update()

                    # Append generated code to the context text area
                    self.context_text.insert(tk.END, f"\n\n```python\n{generated_code}\n```\n")
                    self.context_text.see(tk.END)
                    self.root.update_idletasks()

                else:
                    self.generated_code_text.config(state=tk.NORMAL)
                    self.generated_code_text.delete("1.0", tk.END)
                    self.generated_code_text.insert(tk.END, "No executable Python code detected in response.")
                    self.generated_code_text.config(state=tk.DISABLED)
                    self.run_code_button.config(state=tk.DISABLED) # Disable run button if no code
                    self.edit_code_button.config(state=tk.DISABLED) # Disable edit button if no code
                
                self.status_var.set("Query completed")
            else:
                self.status_var.set("Generation stopped by user.")
            
        except Exception as e:
            if not self.stop_event.is_set(): # Only show error if not stopped by user
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                self.status_var.set("Error occurred")
            else:
                self.status_var.set("Generation stopped by user.")
        finally:
            self.submit_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED) # Disable stop button after completion or stop
            self.root.update()

    def _add_to_chat_history(self, prompt: str, response: str):
        """Adds the prompt and response to the chat history."""
        self.chat_history.append({"prompt": prompt, "response": response})
        self.chat_history_text.config(state=tk.NORMAL)
        self.chat_history_text.insert(tk.END, f"User: {prompt}\n")
        self.chat_history_text.insert(tk.END, f"Model: {response}\n\n")
        self.chat_history_text.see(tk.END)
        self.chat_history_text.config(state=tk.DISABLED)

    def _extract_python_code(self, model_response: str) -> str:
        """
        Attempts to extract and format Python code from the model's response.
        Looks for markdown code blocks.
        """
        code_start_marker = "```python"
        code_end_marker = "```"
        
        start_index = model_response.find(code_start_marker)
        if start_index != -1:
            start_index += len(code_start_marker)
            end_index = model_response.find(code_end_marker, start_index)
            if end_index != -1:
                return model_response[start_index:end_index].strip()
            else:
                # If no end marker, assume rest is code
                return model_response[start_index:].strip()
        return "" # Return empty string if no code block found
    
    def run_generated_code(self):
        """Executes the Python code displayed in the generated_code_text widget."""
        code_to_run = self.generated_code_text.get("1.0", tk.END).strip()
        if not code_to_run:
            messagebox.showinfo("Run Code", "No Python code to run.")
            return

        self.code_output_text.config(state=tk.NORMAL)
        self.code_output_text.delete("1.0", tk.END)
        self.code_output_text.insert(tk.END, "Executing code...\n")
        self.code_output_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

        self.stop_code_event.clear() # Clear the stop event for a new execution
        # Clear any pending input in the queue
        while not self.code_input_queue.empty():
            try:
                self.code_input_queue.get_nowait()
            except queue.Empty:
                pass

        self.run_code_button.config(state=tk.DISABLED)
        self.stop_code_button.config(state=tk.NORMAL) # Enable stop code button
        self.code_input_entry.config(state=tk.NORMAL) # Enable code input
        self.send_code_input_button.config(state=tk.NORMAL) # Enable send input button

        # Run code in a separate thread to prevent GUI freeze
        threading.Thread(target=execute_code_task, args=(self, code_to_run,)).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaMultiModelGUI(root)
    root.mainloop()