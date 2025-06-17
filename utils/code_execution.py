import subprocess
import threading
import queue
import sys
import os
import tkinter as tk # For messagebox and status_var updates

def execute_code_task(gui_instance, code: str):
    """Task to execute Python code and update output."""
    temp_file_path = "temp_generated_code.py"
    try:
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(code)

        gui_instance.current_code_process = subprocess.Popen(
            [sys.executable, temp_file_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1
        )
        
        stdout_thread = threading.Thread(target=_read_stdout, args=(gui_instance, gui_instance.current_code_process, gui_instance.code_output_text, gui_instance.stop_code_event))
        stderr_thread = threading.Thread(target=_read_stderr, args=(gui_instance, gui_instance.current_code_process, gui_instance.code_output_text, gui_instance.stop_code_event))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        while gui_instance.current_code_process.poll() is None:
            if gui_instance.stop_code_event.is_set():
                print("Stop code execution event detected. Terminating process.")
                gui_instance.current_code_process.terminate()
                try:
                    gui_instance.current_code_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if gui_instance.current_code_process.poll() is None:
                        gui_instance.current_code_process.kill()
                gui_instance.status_var.set("Code execution stopped by user.")
                break
            
            gui_instance.root.update_idletasks()
            threading.Event().wait(0.05)

        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

        if not gui_instance.stop_code_event.is_set():
            gui_instance.status_var.set("Code execution completed.")

    except Exception as e:
        if not gui_instance.stop_code_event.is_set():
            gui_instance.code_output_text.config(state=tk.NORMAL)
            gui_instance.code_output_text.delete("1.0", tk.END)
            gui_instance.code_output_text.insert(tk.END, f"--- Execution Error ---\n{str(e)}\n")
            gui_instance.code_output_text.see(tk.END)
            gui_instance.code_output_text.config(state=tk.DISABLED)
            gui_instance.status_var.set("Error during code execution.")
        else:
            gui_instance.status_var.set("Code execution stopped by user.")
    finally:
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception as e:
            print(f"Error cleaning up temp file: {e}")
        
        gui_instance.run_code_button.config(state=tk.NORMAL)
        gui_instance.stop_code_button.config(state=tk.DISABLED)
        gui_instance.code_input_entry.config(state=tk.DISABLED)
        gui_instance.send_code_input_button.config(state=tk.DISABLED)
        gui_instance.current_code_process = None
        gui_instance.root.update_idletasks()

def _read_stdout(gui_instance, process, output_widget, stop_event):
    """Reads stdout from the subprocess and updates the GUI."""
    for line in iter(process.stdout.readline, ''):
        if stop_event.is_set():
            break
        gui_instance.root.after(0, _update_output_widget, output_widget, line)
    process.stdout.close()

def _read_stderr(gui_instance, process, output_widget, stop_event):
    """Reads stderr from the subprocess and updates the GUI."""
    for line in iter(process.stderr.readline, ''):
        if stop_event.is_set():
            break
        gui_instance.root.after(0, _update_output_widget, output_widget, line, "red")
    process.stderr.close()

def _update_output_widget(widget, content, color=None):
    """Helper to update a text widget from a non-GUI thread."""
    widget.config(state=tk.NORMAL)
    if color:
        widget.tag_config(color, foreground=color)
        widget.insert(tk.END, content, color)
    else:
        widget.insert(tk.END, content)
    widget.see(tk.END)
    widget.config(state=tk.DISABLED)
    widget.update_idletasks()