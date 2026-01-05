import gspread
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.gc = None
        self.sh = None
        self.connect()

    def connect(self):
        creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'service_account.json')
        sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'DiscordBotTasks')
        
        # Fallback if specific file is not found but default exists
        if not os.path.exists(creds_file) and os.path.exists('service_account.json'):
            print(f"Warning: Configured '{creds_file}' not found. Using 'service_account.json' instead.")
            creds_file = 'service_account.json'
            
        try:
            self.gc = gspread.service_account(filename=creds_file)
            try:
                self.sh = self.gc.open(sheet_name)
            except gspread.SpreadsheetNotFound:
                # We can't easily create and share, so we hope it exists. 
                # If we create, it's private to the service account.
                # Attempting to create anyway just in case they added the service account to a folder or something?
                # Actually, safe to just error out or print warning if not found.
                print(f"Spreadsheet '{sheet_name}' not found. Please create it and share with the service account.")
                return 

            # Ensure headers match user request
            ws = self.sh.sheet1
            headers = ws.row_values(1)
            # Schema from user image: Status, Group, Assigned By, Assigned To, Due Date, Task Name, Task Inform, Link
            expected_headers = ['Status', 'Group', 'Assigned By', 'Assigned To', 'Due Date', 'Task Name', 'Task Information', 'Link']
            
            # If empty, set headers
            if not headers:
                ws.append_row(expected_headers)
            
        except Exception as e:
            print(f"Database connection failed: {e}")

    def add_task(self, description, assignee_id, author_id, due_date, channel_id, jump_url):
        if not self.sh:
            self.connect()
        
        if not self.sh:
             raise Exception("Database not connected. Check server logs for API errors.")

        ws = self.sh.sheet1
        
        # Columns: Status, Group, Assigned By, Assigned To, Due Date, Task Name, Task Inform, Link
        # Mapped: 'Pending', 'General', author_id, assignee_id, due_date, description, channel_id, jump_url
        
        ws.append_row(['Pending', 'General', str(author_id), str(assignee_id), str(due_date), description, str(channel_id), jump_url])
        return jump_url # Return unique identifier

    def get_pending_tasks(self):
        if not self.sh:
            self.connect()
        if not self.sh:
            return []
        ws = self.sh.sheet1
        return ws.get_all_records()

    def update_task_status(self, task_link, new_status):
        if not self.sh:
            self.connect()
        if not self.sh:
            return
        ws = self.sh.sheet1
        
        # Find row by Link (Col 8)
        try:
            cell = ws.find(task_link)
            # Status is Col 1
            ws.update_cell(cell.row, 1, new_status)
        except gspread.CellNotFound:
            print(f"Task with link {task_link} not found.")



db = Database()
