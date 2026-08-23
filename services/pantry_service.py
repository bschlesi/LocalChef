import os
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
PANTRY_CSV_PATH = os.path.join(DATA_DIR, 'pantry.csv')
CSV_HEADERS = ['Date Added/Updated', 'Item', 'Quantity', 'Unit(s)']


def ensure_pantry_file_exists():
    """Ensures data directory and pantry.csv exist with appropriate headers."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PANTRY_CSV_PATH):
        with open(PANTRY_CSV_PATH, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def get_all_items() -> List[Dict[str, Any]]:
    """Reads all pantry items from pantry.csv."""
    ensure_pantry_file_exists()
    items = []
    with open(PANTRY_CSV_PATH, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row or not any(row.values()):
                continue
            
            # Normalize keys
            date_val = row.get('Date Added/Updated') or row.get('Date') or row.get('date_added') or ''
            item_val = row.get('Item') or row.get('item') or ''
            qty_raw = row.get('Quantity') or row.get('quantity') or 0
            units_val = row.get('Unit(s)') or row.get('Units') or row.get('Unit') or row.get('units') or ''
            
            try:
                qty_val = float(qty_raw) if qty_raw != '' else 0.0
                # Format float nicely if whole number
                if qty_val.is_integer():
                    qty_val = int(qty_val)
            except (ValueError, TypeError):
                qty_val = qty_raw

            if item_val.strip():
                items.append({
                    'date_added': date_val.strip(),
                    'item': item_val.strip(),
                    'quantity': qty_val,
                    'units': units_val.strip()
                })
    return items


def save_all_items(items: List[Dict[str, Any]]):
    """Overwrites pantry.csv with given items list."""
    ensure_pantry_file_exists()
    with open(PANTRY_CSV_PATH, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for it in items:
            writer.writerow([
                it.get('date_added', datetime.now().strftime('%Y-%m-%d')),
                it.get('item', ''),
                it.get('quantity', ''),
                it.get('units', '')
            ])


def add_item(item: str, quantity: Any, units: str = '', date_added: Optional[str] = None) -> Dict[str, Any]:
    """Adds or updates a single item in the pantry."""
    if not item or not item.strip():
        raise ValueError("Item name cannot be empty.")
    
    if not date_added:
        date_added = datetime.now().strftime('%Y-%m-%d')
    
    try:
        qty_num = float(quantity)
        if qty_num.is_integer():
            qty_num = int(qty_num)
    except (ValueError, TypeError):
        qty_num = quantity

    new_item = {
        'date_added': date_added,
        'item': item.strip(),
        'quantity': qty_num,
        'units': units.strip()
    }
    
    items = get_all_items()
    # Check if item already exists (case-insensitive) - update it if so
    found = False
    for existing in items:
        if existing['item'].lower() == item.strip().lower():
            existing['date_added'] = date_added
            existing['quantity'] = qty_num
            existing['units'] = units.strip()
            found = True
            break
            
    if not found:
        items.append(new_item)
        
    save_all_items(items)
    return new_item


def add_items(items_to_add: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Adds or updates multiple items in the pantry."""
    current_items = get_all_items()
    current_map = {it['item'].lower(): it for it in current_items}
    
    for entry in items_to_add:
        item_name = str(entry.get('item', '')).strip()
        if not item_name:
            continue
        
        qty_raw = entry.get('quantity', 0)
        try:
            qty_num = float(qty_raw)
            if qty_num.is_integer():
                qty_num = int(qty_num)
        except (ValueError, TypeError):
            qty_num = qty_raw
            
        units_val = str(entry.get('units', '')).strip()
        date_val = str(entry.get('date_added') or datetime.now().strftime('%Y-%m-%d')).strip()
        
        lower_name = item_name.lower()
        if lower_name in current_map:
            current_map[lower_name]['date_added'] = date_val
            current_map[lower_name]['quantity'] = qty_num
            current_map[lower_name]['units'] = units_val
        else:
            new_entry = {
                'date_added': date_val,
                'item': item_name,
                'quantity': qty_num,
                'units': units_val
            }
            current_items.append(new_entry)
            current_map[lower_name] = new_entry

    save_all_items(current_items)
    return current_items


def remove_items(item_names: List[str]) -> List[Dict[str, Any]]:
    """Removes items by their item names."""
    names_to_remove = {name.strip().lower() for name in item_names if name and name.strip()}
    current_items = get_all_items()
    filtered = [it for it in current_items if it['item'].lower() not in names_to_remove]
    save_all_items(filtered)
    return filtered


def clear_pantry():
    """Removes all items from pantry.csv."""
    save_all_items([])


def import_csv(filename: str = 'pantry_import.csv') -> Dict[str, Any]:
    """
    Looks in ./data directory for the specified CSV file,
    reads and parses it, and updates the pantry.
    Returns summary or raises FileNotFoundError / ValueError.
    """
    import_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(import_path):
        # Look for any .csv in ./data except pantry.csv and pantry_template.csv
        csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and f not in ('pantry.csv', 'pantry_template.csv')]
        if csv_files:
            import_path = os.path.join(DATA_DIR, csv_files[0])
            filename = csv_files[0]
        else:
            raise FileNotFoundError(f"No CSV file found to import in {DATA_DIR}. Please place '{filename}' in the data folder.")

    imported_items = []
    with open(import_path, mode='r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("Import CSV is empty or has no header row.")
        
        for row in reader:
            # Map columns flexibly
            date_val = (
                row.get('Date Added/Updated') or row.get('Date') or 
                row.get('date_added') or row.get('date') or 
                datetime.now().strftime('%Y-%m-%d')
            )
            item_val = row.get('Item') or row.get('item') or row.get('Name') or row.get('name') or ''
            qty_raw = row.get('Quantity') or row.get('quantity') or row.get('Qty') or row.get('qty') or 1
            units_val = (
                row.get('Unit(s)') or row.get('Units') or 
                row.get('Unit') or row.get('units') or 
                row.get('unit') or ''
            )

            if item_val and item_val.strip():
                try:
                    qty_num = float(qty_raw)
                    if qty_num.is_integer():
                        qty_num = int(qty_num)
                except (ValueError, TypeError):
                    qty_num = qty_raw
                    
                imported_items.append({
                    'date_added': str(date_val).strip(),
                    'item': str(item_val).strip(),
                    'quantity': qty_num,
                    'units': str(units_val).strip()
                })

    if not imported_items:
        raise ValueError("No valid item rows found in the imported CSV.")

    add_items(imported_items)
    return {
        'filename': filename,
        'count': len(imported_items),
        'items': imported_items
    }


def format_pantry_for_prompt() -> str:
    """Formats the current pantry into a clean string for LLM prompts."""
    items = get_all_items()
    if not items:
        return "The pantry is currently empty."
    
    lines = []
    for it in items:
        unit_str = f" {it['units']}" if it['units'] else ""
        lines.append(f"- {it['item']}: {it['quantity']}{unit_str} (added: {it['date_added']})")
    return "\n".join(lines)
