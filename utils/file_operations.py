import tkinter as tk
from tkinter import filedialog, messagebox
import os

def save_script_function(gui_instance):
    """Saves the generated code to a .py file."""
    code_to_save = gui_instance.generated_code_text.get("1.0", tk.END).strip()
    if not code_to_save:
        messagebox.showinfo("Save Code", "No Python code to save.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".py",
        filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        title="Save Generated Python Script"
    )

    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code_to_save)
            gui_instance.status_var.set(f"Code saved to {os.path.basename(file_path)}")
            messagebox.showinfo("Save Code", f"Python script saved successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save script: {e}")
            gui_instance.status_var.set("Error saving code.")

def load_script_function(gui_instance):
    """Loads code from a .py file into the generated_code_text area."""
    file_path = filedialog.askopenfilename(
        defaultextension=".py",
        filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        title="Load Python Script"
    )

    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_code = f.read()
            
            gui_instance.generated_code_text.config(state=tk.NORMAL)
            gui_instance.generated_code_text.delete("1.0", tk.END)
            gui_instance.generated_code_text.insert(tk.END, loaded_code)
            gui_instance.generated_code_text.config(state=tk.DISABLED)
            gui_instance.status_var.set(f"Code loaded from {os.path.basename(file_path)}")
            messagebox.showinfo("Load Code", f"Python script loaded successfully from:\n{file_path}")
            
            gui_instance.run_code_button.config(state=tk.NORMAL)
            gui_instance.edit_code_button.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load script: {e}")
            gui_instance.status_var.set("Error loading code.")