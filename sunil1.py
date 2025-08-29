import ast
import re
import copy
import json
from pprint import pprint

# --- CONFIGURATION ---
FILE_PATH = '/home/jon/sunil1.env' # Make sure this points to your file

def load_env_data(file_path):
    """
    Reads and parses a .env-style file.
    - Simple key-value pairs are loaded into a list of single-item dictionaries.
    - JSON string values are parsed into their own lists of dictionaries.
    """
    all_data = {}
    config_vars_list = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None

    pattern = re.compile(r'^\s*([\w.-]+)\s*=\s*(.*)\s*$', re.MULTILINE)
    matches = pattern.finditer(content)

    for match in matches:
        key, value_str = match.groups()
        
        if value_str.startswith("'[") and value_str.endswith("]'"):
            try:
                json_data = value_str.strip("'")
                list_data = json.loads(json_data)
                all_data[key] = {
                    'type': 'list',
                    'data': list_data
                }
            except json.JSONDecodeError:
                print(f"Warning: Could not parse JSON for key '{key}'. Storing as string.")
                config_vars_list.append({key: value_str})
        else:
            try:
                value = ast.literal_eval(value_str)
            except (ValueError, SyntaxError):
                value = value_str.strip('"')
            config_vars_list.append({key: value})

    if config_vars_list:
        all_data['config_vars'] = {
            'type': 'list',
            'data': config_vars_list
        }

    if not all_data:
        print("No data sets found in the file.")
        return None
        
    print(f"Successfully loaded {len(all_data)} data sets.")
    return all_data

def save_env_data(file_path, all_data):
    """
    Saves the data back to the file in the .env format.
    """
    new_content = ""
    
    if 'config_vars' in all_data:
        for item_dict in all_data['config_vars']['data']:
            for key, value in item_dict.items():
                if isinstance(value, str) and (' ' in value or '#' in value):
                    new_content += f'{key}="{value}"\n'
                else:
                    new_content += f'{key}={value}\n'
        new_content += "\n"

    for name, info in all_data.items():
        if name != 'config_vars' and info['type'] == 'list':
            json_str = json.dumps(info['data'])
            new_content += f"{name}='{json_str}'\n"
            
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content.strip() + '\n')
        print(f"All changes have been successfully saved to '{file_path}'.")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def find_item_in_list(data_list, key_to_find):
    """Finds an item in a list of dictionaries by a key or a primary ID."""
    if not data_list: return None, -1, None
    
    # For config_vars, the key is the dictionary key itself.
    if len(data_list[0]) == 1:
        for i, item_dict in enumerate(data_list):
            if key_to_find in item_dict:
                return item_dict, i, "key" # Return "key" as the identifier type
        return None, -1, "key"

    # For complex lists, find the primary ID key (e.g., 'orderId')
    id_key = next((k for k in data_list[0] if 'id' in k.lower()), None)
    if not id_key: return None, -1, None
    
    for i, item_dict in enumerate(data_list):
        if str(item_dict.get(id_key, '')).lower() == key_to_find.lower():
            return item_dict, i, id_key
    return None, -1, id_key

def print_menu(active_set=None, id_key_name=None):
    """Displays the main menu of commands."""
    print("\n--- Interactive Config Editor ---")
    if active_set:
        print(f"Active list: '{active_set}'.")
        if id_key_name:
            print(f"   Use the '{id_key_name}' to identify items (e.g., show <{id_key_name}>).")
    print("\nCommands:")
    print("  list          - Show all available data sets.")
    print("  use <set>     - Select a data set to edit.")
    print("  show <key>    - Show an item by its key/ID.")
    print("  delete <key>  - Delete an item by its key/ID.")
    print("  alter <key>   - Alter an item by its key/ID.")
    print("  add           - Add a new item to the active list.")
    print("  help          - Show this menu again.")
    print("  exit          - Exit the program.")
    print("---------------------------------")

# --- Main Program Execution ---
if __name__ == "__main__":
    all_data = load_env_data(FILE_PATH)
    if not all_data:
        exit()

    original_data = copy.deepcopy(all_data)
    has_unsaved_changes = False
    
    active_set = 'config_vars' if 'config_vars' in all_data else next(iter(all_data), None)
    
    # Determine the initial ID key for the active set
    _, _, id_key = find_item_in_list(all_data[active_set]['data'] if active_set else [], '')
    print_menu(active_set, id_key)

    while True:
        prompt = f"({active_set})> " if active_set else "> "
        command_input = input(prompt).strip()
        
        parts = command_input.split()
        if not parts: continue
            
        command = parts[0].lower()
        args = parts[1:]
        
        if not active_set and command not in ['list', 'use', 'help', 'exit']:
            print("No list active. Use 'use <list_name>' to select one.")
            continue

        if command in ['show', 'delete', 'alter']:
            if not args:
                print(f"Usage: {command} <key_or_id>")
                continue
            
            key_to_find = " ".join(args)
            data_list = all_data[active_set]['data']
            found_item, found_index, id_key = find_item_in_list(data_list, key_to_find)

            if not found_item:
                print(f"Error: Item with {id_key or 'key'}/ID '{key_to_find}' not found in '{active_set}'.")
                continue

            action_taken = False
            if command == 'show':
                pprint(found_item)
            elif command == 'delete':
                if input(f"  Delete item '{key_to_find}'? (y/n): ").lower() == 'y':
                    data_list.pop(found_index)
                    print(f"  [DELETED] Item '{key_to_find}'.")
                    action_taken = True
            elif command == 'alter':
                if len(found_item) == 1: # Simple config var
                    key = list(found_item.keys())[0]
                    new_value_str = input(f"  Enter new value for '{key}': ").strip()
                    try: value = ast.literal_eval(new_value_str)
                    except (ValueError, SyntaxError): value = new_value_str.strip('"')
                    found_item[key] = value
                    print(f"  [ALTERED] '{key}' is now '{value}'.")
                    action_taken = True
                else: # Complex list item
                    print("Enter key-value pairs to update. Empty key to finish.")
                    update_dict = {}
                    while True:
                        key = input("  Enter key to update/add: ").strip()
                        if not key: break
                        value = input(f"  Enter new value for '{key}': ").strip()
                        update_dict[key] = value
                    if update_dict:
                        found_item.update(update_dict)
                        print(f"  [ALTERED] Item '{key_to_find}'.")
                        action_taken = True
            
            if action_taken:
                has_unsaved_changes = True
                if input("  Save this change now? (y/n): ").lower() == 'y':
                    if save_env_data(FILE_PATH, all_data):
                        original_data = copy.deepcopy(all_data)
                        has_unsaved_changes = False # Reset since it's saved
            continue

        if command == 'help':
            _, _, id_key = find_item_in_list(all_data[active_set]['data'] if active_set else [], '')
            print_menu(active_set, id_key)
        elif command == 'list':
            print("\nAvailable data sets:")
            for name in all_data.keys(): print(f"  - {name}")
        elif command == 'use':
            if not args:
                print("Usage: use <data_set_name>")
                continue
            set_name = args[0]
            if set_name in all_data:
                active_set = set_name
                _, _, id_key = find_item_in_list(all_data[active_set]['data'], '')
                print(f"Now editing '{active_set}'.")
                print_menu(active_set, id_key)
            else:
                print(f"Error: Data set '{set_name}' not found.")
        elif command == 'add':
            print("Enter key-value pairs for the new item. Empty key to finish.")
            new_dict = {}
            while True:
                key = input("  Enter key: ").strip()
                if not key: break
                value_str = input(f"  Enter value for '{key}': ").strip()
                try: value = ast.literal_eval(value_str)
                except (ValueError, SyntaxError): value = value_str.strip('"')
                new_dict[key] = value
            if new_dict:
                if active_set == 'config_vars' and len(new_dict) > 1:
                    print("Error: Can only add one key-value pair at a time to config_vars.")
                else:
                    all_data[active_set]['data'].append(new_dict)
                    print(f"  [ADDED] New item to '{active_set}'.")
                    has_unsaved_changes = True
                    if input("  Save this change now? (y/n): ").lower() == 'y':
                        if save_env_data(FILE_PATH, all_data):
                            original_data = copy.deepcopy(all_data)
                            has_unsaved_changes = False # Reset since it's saved
        elif command == 'exit':
            if has_unsaved_changes:
                if input("You have unsaved changes. Exit without saving? (y/n): ").lower() != 'y':
                    continue
            print("Exiting program. Goodbye!")
            break
        else:
            if command_input: print(f"Unknown command: '{command_input}'. Type 'help'.")
