import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
import datetime
import re

# Die Daten werden ab sofort direkt in die HTML-Datei geschrieben.
HTML_FILE = os.path.join(os.path.dirname(__file__), "index.html")

class EditableTreeview(ttk.Treeview):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.bind("<Double-1>", self.on_double_click)
        self.bind("<Delete>", self.on_delete)
        
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Zeile davor einfügen", command=self.insert_row)
        self.menu.add_command(label="Zeile löschen", command=self.delete_row)
        self.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        item = self.identify_row(event.y)
        if item:
            self.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def insert_row(self):
        sel = self.selection()
        if sel:
            item = sel[0]
            index = self.index(item)
            self.insert("", index, values=("", ""))

    def delete_row(self):
        for item in self.selection():
            if item != self.get_children()[-1]:
                self.delete(item)

    def on_delete(self, event):
        self.delete_row()

    def on_double_click(self, event):
        row_id = self.identify_row(event.y)
        column_id = self.identify_column(event.x)
        if not row_id or not column_id:
            return
        col_index = int(column_id[1:]) - 1
        self.edit_cell(row_id, col_index)

    def edit_cell(self, row_id, col_index):
        if not row_id or col_index is None: return
        self.selection_set(row_id)
        self.see(row_id)
        
        column_id = f"#{col_index+1}"
        x, y, width, height = self.bbox(row_id, column_id)
        
        values = list(self.item(row_id, "values"))
        val = values[col_index] if len(values) > col_index else ""

        entry = tk.Entry(self)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, val)
        entry.focus_set()
        
        def save_edit(e=None):
            if not entry.winfo_exists(): return
            new_val = entry.get()
            while len(values) <= col_index:
                values.append("")
            values[col_index] = new_val
            self.item(row_id, values=values)
            entry.destroy()
            
            children = self.get_children()
            if row_id == children[-1] and any(str(v).strip() for v in values):
                self.insert("", tk.END, values=("", ""))

        def on_tab(e):
            save_edit()
            next_col = col_index + 1
            next_row = row_id
            children = self.get_children()
            
            if next_col > 1:
                next_col = 0
                idx = children.index(row_id)
                children = self.get_children()
                if idx + 1 < len(children):
                    next_row = children[idx + 1]
                else:
                    next_row = None
            
            if next_row is not None:
                self.after(10, lambda: self.edit_cell(next_row, next_col))
            return "break"

        entry.bind("<Return>", lambda e: save_edit())
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", lambda e: entry.destroy())
        entry.bind("<Tab>", on_tab)

class RecipeManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🍴 Rezept-Verwaltung am PC")
        self.geometry("950x850")
        
        self.tree_ing: EditableTreeview
        self.text_notes: tk.Text
        
        self.data = {"recipes": [], "last_updated": ""}
        self.recipes = []
        self.current_id = None
        
        self.load_data()
        self.setup_ui()
        self.refresh_listbox()

    def load_data(self):
        if not os.path.exists(HTML_FILE):
            self.data = {"recipes": [], "last_updated": ""}
            self.recipes = []
            return
            
        try:
            with open(HTML_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Extrahiere das JSON aus dem script-Block
            match = re.search(r'<script id="recipe-data">\s*window\.APP_RECIPES\s*=\s*(.*?);\s*</script>', content, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                if json_str:
                    self.data = json.loads(json_str)
                    self.recipes = self.data.get("recipes", [])
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Daten nicht aus index.html laden:\n{e}")

    def save_data(self, show_msg=True):
        self.data["recipes"] = self.recipes
        self.data["last_updated"] = datetime.datetime.now().isoformat()
        
        json_str = json.dumps(self.data, ensure_ascii=False)
        
        try:
            if not os.path.exists(HTML_FILE):
                if show_msg: messagebox.showerror("Fehler", "index.html nicht gefunden!")
                return False
                
            with open(HTML_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Ersetze den alten JSON-String durch den neuen
            new_content = re.sub(
                r'(<script id="recipe-data">\s*window\.APP_RECIPES\s*=\s*)(.*?)(;\s*</script>)',
                lambda m: m.group(1) + json_str + m.group(3),
                content,
                flags=re.DOTALL
            )
            
            with open(HTML_FILE, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            if show_msg: messagebox.showinfo("Erfolg", "Alle Rezepte erfolgreich in index.html gespeichert!")
            return True
        except Exception as e:
            if show_msg: messagebox.showerror("Fehler", f"Fehler beim Speichern in index.html:\n{e}")
            return False

    def setup_ui(self):
        # LEFT PANEL: Listbox
        list_frame = tk.Frame(self, width=250, bg="#f0f0f0")
        list_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        tk.Label(list_frame, text="Vorhandene Rezepte", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=5)
        
        self.listbox = tk.Listbox(list_frame, font=("Arial", 11), width=30)
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        
        scroll = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scroll.set)
        
        # RIGHT PANEL: Form
        form_frame = tk.Frame(self)
        form_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Button Frame in Form Frame anstatt List Frame
        btn_frame = tk.Frame(form_frame)
        btn_frame.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="w")
        
        tk.Button(btn_frame, text="💾 Speichern", command=self.save_current, bg="#bfdbfe", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="+ Neues Rezept", command=self.clear_form, bg="#dcfce7", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📄 Als PDF drucken", command=self.export_pdf, bg="#e2e8f0", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑 Löschen", command=self.delete_current, bg="#fee2e2", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🚪 Beenden", command=self.exit_and_save, bg="#fef08a", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        tk.Label(form_frame, text="Rezept-Details", font=("Arial", 16, "bold")).grid(row=1, column=0, columnspan=2, pady=10, sticky="w")
        
        # Grid fields
        tk.Label(form_frame, text="Name:").grid(row=2, column=0, sticky="e", pady=5)
        self.entry_name = tk.Entry(form_frame, width=40, font=("Arial", 11))
        self.entry_name.grid(row=2, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Kategorien:\n(Komma-getrennt)").grid(row=3, column=0, sticky="e", pady=5)
        self.entry_cat = tk.Entry(form_frame, width=40, font=("Arial", 11))
        self.entry_cat.grid(row=3, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Portionen:").grid(row=4, column=0, sticky="e", pady=5)
        self.entry_port = tk.Entry(form_frame, width=40, font=("Arial", 11))
        self.entry_port.grid(row=4, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Zeit:").grid(row=5, column=0, sticky="e", pady=5)
        self.entry_time = tk.Entry(form_frame, width=40, font=("Arial", 11))
        self.entry_time.grid(row=5, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Energie:").grid(row=6, column=0, sticky="e", pady=5)
        self.entry_energy = tk.Entry(form_frame, width=40, font=("Arial", 11))
        self.entry_energy.grid(row=6, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Quelle (Link):").grid(row=7, column=0, sticky="e", pady=5)
        self.entry_source = tk.Entry(form_frame, width=40, font=("Arial", 11))
        self.entry_source.grid(row=7, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Bild (URL/Pfad):").grid(row=8, column=0, sticky="e", pady=5)
        img_frame = tk.Frame(form_frame)
        img_frame.grid(row=8, column=1, sticky="w", pady=5)
        self.entry_image = tk.Entry(img_frame, width=30, font=("Arial", 11))
        self.entry_image.pack(side="left")
        tk.Button(img_frame, text="Durchsuchen", command=self.browse_image).pack(side="left", padx=5)
        
        tk.Label(form_frame, text="Zutaten:").grid(row=9, column=0, sticky="ne", pady=10)
        ing_frame = tk.Frame(form_frame)
        ing_frame.grid(row=9, column=1, sticky="w", pady=10)
        
        style = ttk.Style(self)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        
        cols = ("Amount", "Name")
        self.tree_ing = EditableTreeview(ing_frame, columns=cols, show="headings", height=8)
        self.tree_ing.heading("Amount", text="Menge", anchor="w")
        self.tree_ing.heading("Name", text="Zutat", anchor="w")
        self.tree_ing.column("Amount", width=100)
        self.tree_ing.column("Name", width=250)
        self.tree_ing.pack(side="left", fill="both", expand=True)
        
        ing_scroll = tk.Scrollbar(ing_frame, command=self.tree_ing.yview)
        ing_scroll.pack(side="right", fill="y")
        self.tree_ing.config(yscrollcommand=ing_scroll.set)
        
        tk.Label(form_frame, text="Hinweis: Doppelklick in Zelle zum Bearbeiten.\nRechtsklick um eine neue Zeile dazwischen einzufügen.\nEntf-Taste löscht Zeile.", fg="gray", font=("Arial", 9), justify="left").grid(row=10, column=1, sticky="w", pady=(0, 10))
        
        tk.Label(form_frame, text="Anleitung:\n(Ein Schritt pro Zeile)").grid(row=10, column=0, sticky="ne", pady=10)
        self.text_inst = tk.Text(form_frame, width=50, height=10, font=("Arial", 10))
        self.text_inst.grid(row=10, column=1, sticky="w", pady=10)

        tk.Label(form_frame, text="Anmerkungen:").grid(row=11, column=0, sticky="ne", pady=10)
        self.text_notes = tk.Text(form_frame, width=50, height=4, font=("Arial", 10))
        self.text_notes.grid(row=11, column=1, sticky="w", pady=10)
        
    def browse_image(self):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(filetypes=[("Bilder", "*.png;*.jpg;*.jpeg;*.gif;*.webp")])
        if filepath:
            self.entry_image.delete(0, tk.END)
            self.entry_image.insert(0, filepath)



    def refresh_listbox(self):
        self.recipes.sort(key=lambda r: r['name'].lower())
        self.listbox.delete(0, tk.END)
        for r in self.recipes:
            self.listbox.insert(tk.END, r["name"])

    def clear_form(self):
        self.current_id = None
        self.listbox.selection_clear(0, tk.END)
        self.entry_name.delete(0, tk.END)
        self.entry_cat.delete(0, tk.END)
        self.entry_port.delete(0, tk.END)
        self.entry_time.delete(0, tk.END)
        self.entry_energy.delete(0, tk.END)
        self.entry_source.delete(0, tk.END)
        self.entry_image.delete(0, tk.END)
        for item in self.tree_ing.get_children():
            self.tree_ing.delete(item)
        self.tree_ing.insert("", tk.END, values=("", ""))
        self.text_inst.delete("1.0", tk.END)
        self.text_notes.delete("1.0", tk.END)

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel: return
        idx = sel[0]
        recipe = self.recipes[idx]
        self.current_id = recipe["id"]
        
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, recipe.get("name", ""))
        
        self.entry_cat.delete(0, tk.END)
        self.entry_cat.insert(0, ", ".join(recipe.get("categories", [])))
        
        self.entry_port.delete(0, tk.END)
        self.entry_port.insert(0, recipe.get("portions", ""))
        
        self.entry_time.delete(0, tk.END)
        self.entry_time.insert(0, recipe.get("prep_time", ""))
        
        self.entry_energy.delete(0, tk.END)
        self.entry_energy.insert(0, recipe.get("energy", ""))
        
        self.entry_source.delete(0, tk.END)
        self.entry_source.insert(0, recipe.get("source", ""))
        
        self.entry_image.delete(0, tk.END)
        img_val = recipe.get("image", "")
        if img_val.startswith("data:image"):
            self.entry_image.insert(0, "[Integriertes Bild]")
        else:
            self.entry_image.insert(0, img_val)
        
        # Format ingredients
        ings = recipe.get("ingredients", [])
        for item in self.tree_ing.get_children():
            self.tree_ing.delete(item)
        for ing in ings:
            self.tree_ing.insert("", tk.END, values=(ing.get("amount", ""), ing.get("name", "")))
        self.tree_ing.insert("", tk.END, values=("", ""))
        
        self.text_inst.delete("1.0", tk.END)
        inst_data = recipe.get("instructions", "")
        if isinstance(inst_data, list):
            self.text_inst.insert(tk.END, "\n".join(inst_data))
        else:
            self.text_inst.insert(tk.END, str(inst_data))

        self.text_notes.delete("1.0", tk.END)
        self.text_notes.insert(tk.END, recipe.get("notes", ""))

    def save_current(self, show_msg=True):
        name = self.entry_name.get().strip()
        if not name:
            if show_msg: messagebox.showwarning("Achtung", "Ein Rezept braucht mindestens einen Namen!")
            return False
            
        # Parse ingredients
        ingredients = []
        for item in self.tree_ing.get_children():
            values = self.tree_ing.item(item, "values")
            amt = str(values[0]).strip() if len(values) > 0 else ""
            nme = str(values[1]).strip() if len(values) > 1 else ""
            if amt or nme:
                ingredients.append({"amount": amt, "name": nme})
                
        # Parse categories
        cats = [c.strip() for c in self.entry_cat.get().split(",") if c.strip()]
        
        # Parse instructions
        inst_text = self.text_inst.get("1.0", tk.END).strip()
        inst_lines = [line.strip() for line in inst_text.split("\n") if line.strip()]

        image_val = self.entry_image.get().strip()
        if os.path.isfile(image_val):
            try:
                import base64
                import mimetypes
                with open(image_val, "rb") as img_file:
                    encoded_string = base64.b64encode(img_file.read()).decode("utf-8")
                    mime_type, _ = mimetypes.guess_type(image_val)
                    if not mime_type:
                        mime_type = "image/jpeg"
                    image_val = f"data:{mime_type};base64,{encoded_string}"
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Laden des Bildes:\n{e}")
                return
        elif image_val == "[Integriertes Bild]":
            if self.current_id is not None:
                for r in self.recipes:
                    if r["id"] == self.current_id:
                        image_val = r.get("image", "")
                        break

        recipe_data = {
            "name": name,
            "categories": cats,
            "portions": self.entry_port.get().strip(),
            "prep_time": self.entry_time.get().strip(),
            "energy": self.entry_energy.get().strip(),
            "source": self.entry_source.get().strip(),
            "image": image_val,
            "ingredients": ingredients,
            "instructions": inst_lines,
            "notes": self.text_notes.get("1.0", tk.END).strip()
        }

        if self.current_id is None:
            # Create New
            new_id = max([r["id"] for r in self.recipes] + [0]) + 1
            recipe_data["id"] = new_id
            self.recipes.append(recipe_data)
            self.current_id = new_id
        else:
            # Update Existing
            for r in self.recipes:
                if r["id"] == self.current_id:
                    recipe_data["id"] = self.current_id
                    r.update(recipe_data)
                    break
        
        self.refresh_listbox()
        return self.save_data(show_msg=show_msg)

    def exit_and_save(self):
        name = self.entry_name.get().strip()
        if name:
            self.save_current(show_msg=False)
        else:
            self.save_data(show_msg=False)
        self.destroy()
        
    def delete_current(self):
        if self.current_id is None: return
        if messagebox.askyesno("Löschen", "Soll dieses Rezept wirklich gelöscht werden?"):
            self.recipes = [r for r in self.recipes if r["id"] != self.current_id]
            self.clear_form()
            self.refresh_listbox()
            self.save_data()

    def export_pdf(self):
        if self.current_id is None:
            messagebox.showinfo("Info", "Bitte zuerst ein Rezept auswählen!")
            return
            
        recipe = next((r for r in self.recipes if r["id"] == self.current_id), None)
        if not recipe: return
        
        import tempfile
        import webbrowser
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{recipe.get('name', 'Rezept')}</title>
<style>
    @media print {{
        @page {{ margin: 0; }} /* Versteckt automatisch die Kopf-/Fußzeilen des Browsers */
        body {{ padding: 1.5cm 1.5cm !important; margin: 0 !important; box-sizing: border-box; }} /* Ersatz für den Druck-Rand */
    }}
    body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; line-height: 1.4; max-width: 800px; margin: 0 auto; }}
    h1 {{ color: #f97316; border-bottom: 2px solid #f97316; padding-bottom: 5px; margin-top: 0; margin-bottom: 15px; font-size: 24px; }}
    h2 {{ color: #f97316; margin-top: 20px; border-bottom: 1px solid #eee; padding-bottom: 3px; margin-bottom: 10px; font-size: 18px; }}
    .meta-info {{ display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 15px; background: #f9fafb; padding: 10px 15px; border-radius: 6px; border: 1px solid #e5e7eb; }}
    .meta-item {{ font-size: 13px; }}
    .meta-item strong {{ color: #4b5563; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 13px; line-height: 1.2; }}
    th, td {{ padding: 2px 5px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
    th {{ background-color: #f9fafb; color: #4b5563; font-weight: 600; padding: 4px 5px; }}
    ol {{ padding-left: 20px; margin-top: 5px; font-size: 14px; }}
    li {{ margin-bottom: 6px; }}
    .notes {{ background: #fffbeb; padding: 10px 15px; border-left: 4px solid #fbbf24; margin-top: 5px; white-space: pre-wrap; font-size: 13px; }}
</style>
</head>
<body onload="window.print()">
    <h1>{recipe.get('name', 'Rezept')}</h1>
    <div class="meta-info">"""
        
        if recipe.get('categories'):
            html_content += f'<div class="meta-item"><strong>Kategorien:</strong> {", ".join(recipe.get("categories", []))}</div>'
        if recipe.get('portions'):
            html_content += f'<div class="meta-item"><strong>Portionen:</strong> {recipe.get("portions", "")}</div>'
        if recipe.get('prep_time'):
            html_content += f'<div class="meta-item"><strong>Zeit:</strong> {recipe.get("prep_time", "")}</div>'
        if recipe.get('energy'):
            html_content += f'<div class="meta-item"><strong>Energie:</strong> {recipe.get("energy", "")}</div>'
            
        html_content += """</div>
    
    <h2>Zutaten</h2>
    <table>
        <tr><th style="width: 30%;">Menge</th><th>Zutat</th></tr>"""
        
        for ing in recipe.get('ingredients', []):
            html_content += f"<tr><td>{ing.get('amount','')}</td><td>{ing.get('name','')}</td></tr>"
            
        html_content += """
    </table>
    
    <h2>Zubereitung</h2>
    <ol>"""
    
        inst_data = recipe.get('instructions', [])
        if isinstance(inst_data, str):
            inst_data = [inst_data]
            
        for step in inst_data:
            if step.strip():
                html_content += f"<li>{step}</li>"
                
        html_content += """
    </ol>"""

        if recipe.get('notes'):
            html_content += f"""
    <h2>Anmerkungen</h2>
    <div class="notes">{recipe.get('notes', '')}</div>"""
        
        if recipe.get('source'):
            html_content += f"""<p style="margin-top: 15px; font-size: 12px; color: #9ca3af;">Quelle: {recipe.get('source', '')}</p>"""

        html_content += """
</body>
</html>"""
        
        fd, path = tempfile.mkstemp(suffix=".html")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html_content)
        webbrowser.open('file://' + os.path.realpath(path))

if __name__ == "__main__":
    app = RecipeManagerApp()
    app.mainloop()
