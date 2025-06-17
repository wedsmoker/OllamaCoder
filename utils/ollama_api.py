import requests
import json
import tkinter as tk # For messagebox and status_var updates

def fetch_ollama_models(gui_instance):
    """Fetches available models from the Ollama API and populates the combobox."""
    gui_instance.status_var.set("Fetching models from Ollama...")
    gui_instance.root.update_idletasks()
    try:
        url = f"{gui_instance.ollama_url.rstrip('/')}/api/tags"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        gui_instance.available_models = [model['name'] for model in data.get('models', [])]
        
        if gui_instance.available_models:
            gui_instance.model_combobox['values'] = gui_instance.available_models
            
            if "qwen2.5-coder:3b" in gui_instance.available_models:
                gui_instance.model_combobox.set("qwen2.5-coder:3b")
            else:
                gui_instance.model_combobox.set(gui_instance.available_models[0])
            
            gui_instance.status_var.set("Models loaded.")
        else:
            gui_instance.model_combobox.set("No models found.")
            gui_instance.status_var.set("No Ollama models found. Is Ollama server running?")
    except requests.exceptions.ConnectionError:
        gui_instance.model_combobox.set("Ollama server not reachable.")
        gui_instance.status_var.set("Error: Ollama server not reachable. Please check URL and server status.")
    except Exception as e:
        gui_instance.model_combobox.set("Error loading models.")
        gui_instance.status_var.set(f"Error fetching models: {str(e)}")
    finally:
        gui_instance.model_combobox.config(state="readonly")
        gui_instance.root.update_idletasks()

def query_single_model(
    gui_instance,
    model: str,
    system_message: str,
    context: str,
    question: str,
    temperature: float,
    max_tokens: int,
    ollama_url: str
) -> str:
    """Query a single Ollama model."""
    url = f"{ollama_url.rstrip('/')}/api/chat"
    
    messages = [
        {
            "role": "system",
            "content": system_message
        },
        {
            "role": "user",
            "content": f"Context: {context}\n\nQuestion: {question}"
        }
    ]

    for entry in gui_instance.chat_history:
        messages.append({"role": "user", "content": entry["prompt"]})
        messages.append({"role": "assistant", "content": entry["response"]})
    
    payload = {
        "model": model,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "num_ctx": max_tokens
        },
        "stream": True
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("\n--- Ollama API Request Payload (Messages) ---")
    print(json.dumps(messages, indent=2))
    print("---------------------------------------------\n")

    response = requests.post(url, data=json.dumps(payload), headers=headers, stream=True)
    response.raise_for_status()
    
    full_response = []
    for line in response.iter_lines():
        if gui_instance.stop_event.is_set():
            print("Stop event detected. Closing connection.")
            response.close()
            gui_instance.status_var.set("Generation stopped.")
            break
        if line:
            chunk = json.loads(line.decode('utf-8'))
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                full_response.append(content)
                gui_instance.results_text.insert(tk.END, content)
                gui_instance.results_text.see(tk.END)
                gui_instance.root.update_idletasks()
    
    return ''.join(full_response)