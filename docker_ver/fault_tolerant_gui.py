import tkinter as tk
from tkinter import ttk, messagebox
import threading
from queue import Queue
import os
import sys
import hashlib
import json
from fault_tolerant_gui_client import FaultTolerantGUIClient

def print_usage():
    """Print usage instructions"""
    print("Usage: python fault_tolerant_gui.py <cluster_config_path>")
    print("Example: python fault_tolerant_gui.py cluster_config_client.json")
    sys.exit(1)

class ChatInterface:
    def __init__(self, cluster_config_path):
        print("Initializing ChatInterface...")
        # Initialize the main window
        self.root = tk.Tk()
        self.root.title("Fault-Tolerant Chat Application")
        self.root.geometry("800x600")  # Set a reasonable default size
        
        # Message queue for thread-safe communication
        self.message_queue = Queue()
        
        # User session data
        self.current_user_id = None
        self.current_token = None
        self.message_ids = []

        try:
            self.client = FaultTolerantGUIClient(cluster_config_path)
            if not self.client.connect():
                messagebox.showerror("Connection Error", "Failed to connect to any server in the cluster")
                sys.exit(1)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to initialize client\nError: {str(e)}")
            sys.exit(1)
        
        # Configure grid weights for the root window
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        print("Showing login screen...")
        # Show login screen first
        self.show_login_screen()
    
    def get_username_by_id(self, user_id: int) -> str:
        """Get username by user ID"""
        print(f"Looking up username for ID: {user_id}")
        username = self.client.GetUsernameByID(user_id)
        return username

    def get_userID_by_username(self, username: str) -> int:
        print(f"Finding ID for username: {username}")
        found, user_id = self.client.GetUserByUsername(username)
        return user_id if found else 0
    
    def show_login_screen(self):
        print("Setting up login screen...")
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create login frame
        login_frame = ttk.Frame(self.root, padding="20")
        login_frame.grid(row=0, column=0)
        
        # Configure grid weights for centering
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(login_frame, text="Fault-Tolerant Chat Application", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Instructions
        instructions = ttk.Label(login_frame, 
                               text="Enter username and password\nNew users will be registered automatically",
                               justify=tk.CENTER)
        instructions.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # Username field
        ttk.Label(login_frame, text="Username:").grid(row=2, column=0, pady=5, padx=5, sticky="e")
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.grid(row=2, column=1, pady=5, padx=5, sticky="ew")
        
        # Password field
        ttk.Label(login_frame, text="Password:").grid(row=3, column=0, pady=5, padx=5, sticky="e")
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.grid(row=3, column=1, pady=5, padx=5, sticky="ew")
        
        # Login button
        self.login_button = ttk.Button(login_frame, text="Login", command=self.handle_login)
        self.login_button.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Status label
        self.status_label = ttk.Label(login_frame, text="", foreground="black")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=5)
        
        # Error label
        self.error_label = ttk.Label(login_frame, text="", foreground="red")
        self.error_label.grid(row=6, column=0, columnspan=2, pady=5)
        
        # Bind Enter key to login
        self.username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        self.password_entry.bind('<Return>', lambda e: self.handle_login())
        
        # Set focus to username entry
        self.username_entry.focus()
        print("Login screen setup complete")
    
    def handle_login(self):
        """Handle login button click"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.error_label.config(text="Please enter both username and password")
            return
        
        try:
            # Try to log in first
            success, token, unread_count = self.client.Login(username, password)
            
            if success:
                # Get user ID
                found, user_id = self.client.GetUserByUsername(username)
                if not found:
                    self.error_label.config(text="Failed to get user ID after login")
                    return
                
                self.current_user_id = user_id
                self.current_token = token
                print(f"Login successful. User ID: {user_id}, Token: {token}")
                self.show_main_screen()
                self.check_messages()  # Start checking for messages
                return
            
            # If login failed, try creating account
            print("Login failed, attempting to create account...")
            token = self.client.CreateAccount(username, password)
            if token:
                found, user_id = self.client.GetUserByUsername(username)
                if not found:
                    self.error_label.config(text="Failed to get user ID after account creation")
                    return
                
                self.current_user_id = user_id
                self.current_token = token
                print(f"Account created successfully. User ID: {user_id}, Token: {token}")
                self.show_main_screen()
                self.check_messages()  # Start checking for messages
            else:
                self.error_label.config(text="Failed to create account")
        
        except Exception as e:
            self.error_label.config(text=f"Error: {str(e)}")
            print(f"Login error: {str(e)}")

    def check_messages(self):
        """Periodically check for new messages and update the display"""
        if self.current_user_id and self.current_token:  # Only check if logged in
            print(f"\n=== Checking Messages for User {self.current_user_id} ===")
            
            # Get current selection to maintain it after refresh
            current_selection = None
            if hasattr(self, 'users_list'):
                selected_indices = self.users_list.curselection()
                if selected_indices:
                    current_selection = self.users_list.get(selected_indices[0])
                    if '[NEW]' in current_selection:
                        current_selection = current_selection.replace('[NEW] ', '')
                    if ' (UNREAD:' in current_selection:
                        current_selection = current_selection.split(' (UNREAD:')[0]
                    print(f"[DEBUG] Current selection: {current_selection}")
            
            try:
                # Get unread messages before refresh
                old_unread = self.client.GetUnreadMessages(self.current_user_id, self.current_token)
                old_count = len(old_unread) if old_unread else 0
                print(f"[DEBUG] Unread messages before refresh: {old_count}")
                
                # Refresh lists and counts
                print("[DEBUG] Refreshing user list and unread count...")
                self.refresh_user_list()
                self.update_unread_count()
                
                # Get unread messages after refresh
                new_unread = self.client.GetUnreadMessages(self.current_user_id, self.current_token)
                new_count = len(new_unread) if new_unread else 0
                print(f"[DEBUG] Unread messages after refresh: {new_count}")
                
                # Restore selection if needed
                if current_selection and hasattr(self, 'users_list'):
                    for i in range(self.users_list.size()):
                        item = self.users_list.get(i)
                        clean_item = item.replace('[NEW] ', '').split(' (UNREAD:')[0]
                        if clean_item == current_selection:
                            self.users_list.selection_set(i)
                            self.users_list.see(i)
                            print(f"[DEBUG] Restored selection to: {clean_item}")
                            break
            except Exception as e:
                print(f"Error during message check: {str(e)}")
            
            print("=== Message Check Complete ===\n")
            # Check messages every 3 seconds
            self.root.after(3000, self.check_messages)

    def show_main_screen(self):
        print("\n=== Setting up main screen... ===\n")
        try:
            # Clear login screen
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # Create the main container frame with padding
            self.main_frame = ttk.Frame(self.root, padding="5")
            self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Configure grid weights
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            self.main_frame.columnconfigure(1, weight=1)  # Message area column
            self.main_frame.rowconfigure(2, weight=1)  # Message area row
            
            # Add menu bar
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # File menu
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Delete Account", command=self.handle_delete_account)
            file_menu.add_separator()
            file_menu.add_command(label="Logout", command=self.handle_logout)
            
            # Create unread messages counter at the top
            self.unread_counter_frame = ttk.Frame(self.main_frame)
            self.unread_counter_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            self.unread_counter_label = ttk.Label(self.unread_counter_frame, text="Unread Messages: 0", font=("Helvetica", 10, "bold"))
            self.unread_counter_label.pack()
            
            # Create users list frame (left side)
            users_frame = ttk.LabelFrame(self.main_frame, text="Users", padding="5")
            users_frame.grid(row=1, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
            
            # Users list with scrollbar
            self.users_list = tk.Listbox(users_frame, width=30)
            users_scrollbar = ttk.Scrollbar(users_frame, orient=tk.VERTICAL, command=self.users_list.yview)
            self.users_list.configure(yscrollcommand=users_scrollbar.set)
            
            # Pack users list and scrollbar
            self.users_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            users_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Create message area (right side)
            message_frame = ttk.LabelFrame(self.main_frame, text="Messages", padding="5")
            message_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Message display area with scrollbar
            self.message_display = tk.Text(message_frame, wrap=tk.WORD, state=tk.DISABLED)
            message_scrollbar = ttk.Scrollbar(message_frame, orient=tk.VERTICAL, command=self.message_display.yview)
            self.message_display.configure(yscrollcommand=message_scrollbar.set)
            
            # Pack message display and scrollbar
            self.message_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            message_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Create message input area (bottom right)
            input_frame = ttk.Frame(self.main_frame, padding="5")
            input_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.S))
            
            # Message input field
            self.message_input = ttk.Entry(input_frame)
            self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            # Send button
            send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
            send_button.pack(side=tk.RIGHT)
            
            # Bind events
            self.users_list.bind('<<ListboxSelect>>', self.on_user_select)
            self.message_input.bind('<Return>', lambda e: self.send_message())
            
            # Initial user list population
            self.refresh_user_list()
            self.update_unread_count()
            
            print("Main screen setup complete")
            
        except Exception as e:
            print(f"Error setting up main screen: {str(e)}")
            messagebox.showerror("Error", f"Failed to set up main screen: {str(e)}")

    def refresh_user_list(self):
        """Refresh the list of users"""
        if not self.current_user_id or not self.current_token:
            return
        
        try:
            # Get list of all users
            users = self.client.ListAccounts(self.current_user_id, self.current_token, "*")
            if not users:
                return
            
            # Get unread messages
            unread_messages = self.client.GetUnreadMessages(self.current_user_id, self.current_token)
            unread_by_user = {}
            for msg_id, sender_id, _ in unread_messages:
                unread_by_user[sender_id] = unread_by_user.get(sender_id, 0) + 1
            
            # Clear current list
            self.users_list.delete(0, tk.END)
            
            # Add users to list
            for username in users:
                if username:  # Skip empty usernames
                    found, user_id = self.client.GetUserByUsername(username)
                    if found and user_id != self.current_user_id:
                        display_name = username
                        if user_id in unread_by_user:
                            display_name = f"[NEW] {display_name} (UNREAD: {unread_by_user[user_id]})"
                        self.users_list.insert(tk.END, display_name)
            
        except Exception as e:
            print(f"Error refreshing user list: {str(e)}")

    def update_unread_count(self):
        """Update the unread messages counter"""
        if not self.current_user_id or not self.current_token:
            return
        
        try:
            unread = self.client.GetUnreadMessages(self.current_user_id, self.current_token)
            count = len(unread) if unread else 0
            self.unread_counter_label.config(text=f"Unread Messages: {count}")
        except Exception as e:
            print(f"Error updating unread count: {str(e)}")

    def on_user_select(self, event):
        """Handle user selection from the list"""
        if not self.users_list.curselection():
            return
        
        selected = self.users_list.get(self.users_list.curselection())
        if '[NEW]' in selected:
            selected = selected.replace('[NEW] ', '')
        if ' (UNREAD:' in selected:
            selected = selected.split(' (UNREAD:')[0]
        
        try:
            # Get user ID for selected username
            found, conversant_id = self.client.GetUserByUsername(selected)
            if not found:
                print(f"Could not find user ID for username: {selected}")
                return
            
            # Get conversation
            messages = self.client.DisplayConversation(
                self.current_user_id,
                self.current_token,
                conversant_id
            )
            
            # Clear and update message display
            self.message_display.config(state=tk.NORMAL)
            self.message_display.delete(1.0, tk.END)
            
            for msg_id, content, is_sender in messages:
                sender = "You" if is_sender else selected
                self.message_display.insert(tk.END, f"{sender}: {content}\n")
                self.message_ids.append(msg_id)
            
            self.message_display.config(state=tk.DISABLED)
            self.message_display.see(tk.END)
            
        except Exception as e:
            print(f"Error displaying conversation: {str(e)}")

    def send_message(self):
        """Send a message to the selected user"""
        if not self.users_list.curselection():
            messagebox.showwarning("Warning", "Please select a user to send message to")
            return
        
        message = self.message_input.get().strip()
        if not message:
            return
        
        selected = self.users_list.get(self.users_list.curselection())
        if '[NEW]' in selected:
            selected = selected.replace('[NEW] ', '')
        if ' (UNREAD:' in selected:
            selected = selected.split(' (UNREAD:')[0]
        
        try:
            # Get recipient ID
            found, recipient_id = self.client.GetUserByUsername(selected)
            if not found:
                messagebox.showerror("Error", f"Could not find user ID for: {selected}")
                return
            
            # Send message
            success = self.client.SendMessage(
                self.current_user_id,
                self.current_token,
                recipient_id,
                message
            )
            
            if success:
                # Clear input field
                self.message_input.delete(0, tk.END)
                # Refresh conversation
                self.on_user_select(None)
            else:
                messagebox.showerror("Error", "Failed to send message")
                
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            messagebox.showerror("Error", f"Failed to send message: {str(e)}")

    def handle_delete_account(self):
        """Handle account deletion"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete your account?"):
            try:
                success = self.client.DeleteAccount(self.current_user_id, self.current_token)
                if success:
                    messagebox.showinfo("Success", "Account deleted successfully")
                    self.handle_logout()
                else:
                    messagebox.showerror("Error", "Failed to delete account")
            except Exception as e:
                print(f"Error deleting account: {str(e)}")
                messagebox.showerror("Error", f"Failed to delete account: {str(e)}")

    def handle_logout(self):
        """Handle logout"""
        self.current_user_id = None
        self.current_token = None
        self.message_ids = []
        self.show_login_screen()

    def run(self):
        """Start the chat application"""
        self.root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_usage()
    
    cluster_config_path = sys.argv[1]
    if not os.path.exists(cluster_config_path):
        print(f"Error: Config file {cluster_config_path} does not exist")
        sys.exit(1)
        
    app = ChatInterface(cluster_config_path)
    app.run()
