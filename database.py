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
        sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Task Assign System')
        
        if not os.path.exists(creds_file):
            print(f"⚠️ Warning: '{creds_file}' not found.")
            
        try:
            self.gc = gspread.service_account(filename=creds_file)
            try:
                self.sh = self.gc.open(sheet_name)
                print(f"✅ Successfully connected to Google Sheet: {sheet_name}")
            except gspread.SpreadsheetNotFound:
                print(f"❌ Spreadsheet '{sheet_name}' not found.")
                return 

            # 確保標題列存在
            ws = self.sh.sheet1
            headers = ws.row_values(1)
            expected_headers = ['Status', 'Group', 'Assigned By', 'Assigned To', 'Assigned Date', 'Due Date', 'Task Name', 'Task Information', 'Link']
            
            if not headers:
                ws.append_row(expected_headers)
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")

    def add_task(self, description, assignee_id, author_id, due_date, channel_id, jump_url):
        if not self.sh:
            self.connect()
        ws = self.sh.sheet1
        import datetime
        assigned_date = datetime.datetime.now().strftime("%Y/%m/%d")

        ws.append_row(['Pending', 'General', str(author_id), str(assignee_id), str(assigned_date), str(due_date), description, str(channel_id), jump_url])
        return jump_url

    def get_pending_tasks(self):
        """
        取得所有任務資料。
        注意：gspread 的 get_all_records() 會回傳一個 List，
        List 的 index 0 對應 Excel 的第 2 行 (因為第 1 行是標題)。
        """
        if not self.sh:
            self.connect()
        if not self.sh:
            return []
        try:
            ws = self.sh.sheet1
            return ws.get_all_records()
        except Exception as e:
            print(f"Error reading tasks: {e}")
            return []

    def update_task_status_by_row(self, row_index, new_status):
        """
        直接指定行數 (Row Index) 修改 Status (第 1 欄)。
        """
        if not self.sh:
            self.connect()
        if not self.sh:
            print("❌ Database not connected.")
            return

        ws = self.sh.sheet1
        try:
            # update_cell(行, 列, 值) -> Status 在第 1 欄
            ws.update_cell(row_index, 1, new_status)
            print(f"📝 Database updated: Row {row_index} status set to '{new_status}'")
        except Exception as e:
            print(f"❌ Error updating row {row_index}: {e}")
            # 如果是權限錯誤，這裡會印出來，請務必檢查 Console

db = Database()