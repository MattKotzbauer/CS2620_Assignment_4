import tkinter as tk
from tkinter import ttk, messagebox
import threading
from queue import Queue
from client import Client
import os
import sys
import hashlib
# from client import Client
import json


def print_usage():
    """Print usage instructions"""
    print("Usage: python tkinter_base.py <host> <port>")
    print("Example: python tkinter_base.py 127.0.0.1 65432")
    sys.exit(1)
    
class ChatInterface:
    def __init__(self, host, port):
        print("Initializing ChatInterface...")
        # Initialize the main window
        self.root = tk.Tk()
        self.root.title("Chat Application")
        self.root.geometry("800x600")  # Set a reasonable default size
        
        # Message queue for thread-safe communication
        self.message_queue = Queue()
        
        # User session data
        # NOTE: basically any persistent metadata we want within client session can be initialized here
        self.current_user_id = None
        self.current_token = None
        self.message_ids = []

        try:
            self.client = Client(host=host, port=int(port))
            self.client.connect()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {host}:{port}\nError: {str(e)}")
            sys.exit(1)
        
        # TODO: set as cli parameter
        # self.client.connect()
        
        # Configure grid weights for the root window
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        print("Showing login screen...")
        # Show login screen first
        self.show_login_screen()
    
    def get_username_by_id(self, user_id: int) -> str:
        """Get username by user ID"""
        print(f"Looking up username for ID: {user_id}")
        # user = user_base.users.get(user_id)
        username = self.client.get_username_by_id(user_id)
        return username # (returns None if empty)


    def get_userID_by_username(self, username: str) -> int:
        print(f"Finding ID for username: {username}")
        found, user_id = self.client.get_user_by_username(username)
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
        title_label = ttk.Label(login_frame, text="Chat Application", font=("Helvetica", 16, "bold"))
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
            
            # Get unread messages before refresh
            old_unread = self.client.get_unread_messages(self.current_user_id, self.current_token)
            old_count = len(old_unread) if old_unread else 0
            print(f"[DEBUG] Unread messages before refresh: {old_count}")
            
            # Refresh lists and counts
            print("[DEBUG] Refreshing user list and unread count...")
            self.refresh_user_list()
            self.update_unread_count()
            
            # Get unread messages after refresh
            new_unread = self.client.get_unread_messages(self.current_user_id, self.current_token)
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
            
            # Create the UI components
            self.create_user_list()
            self.create_message_area()
            self.create_input_area()
            
            # Start message checking thread
            self.message_check_thread = threading.Thread(target=self.check_messages, daemon=True)
            self.message_check_thread.start()
            
            # Initial refresh of user list
            self.refresh_user_list()
            
            print("\n=== Main screen setup complete ===\n")
            
        except Exception as e:
            print(f"\n!!! Error setting up main screen: {str(e)} !!!\n")
            import traceback
            traceback.print_exc()
    
    def handle_login(self):
        print("\n=== Login/Signup Attempt ===\n")
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.error_label.config(text="Please enter both username and password")
            return
            
        print(f"Username entered: {username}")
        hashed_password = self.client.hash_password(password)
        print(f"Password hashed for {username}")
        
        # Check if user exists
        print(f"Looking up user object for username: {username}")
        userID = self.get_userID_by_username(username) # (valid)
        print(f"User lookup result: {userID}")
        
        # Handle non-existent user
        if not userID:
            print(f"\n=== User Not Found Flow ===\n")
            print(f"1. Detected missing user: {username}")
            
            # Show account creation dialog
            try:
                print("2. Showing account creation dialog...")
                should_create = messagebox.askyesno(
                    "Create New Account",
                    f"User '{username}' does not exist. Would you like to create a new account?",
                    icon='question',
                    parent=self.root
                )
                
                if not should_create:
                    print("3. User declined account creation")
                    self.error_label.config(text="Login canceled - user doesn't exist")
                    return
                
                print("3. Creating new account...")
                try:
                    self.current_token = self.client.create_account(username, hashed_password)
                    userID = self.get_userID_by_username(username)
                    if not userID:
                        raise Exception("Failed to create account")
                    
                    self.current_user_id = userID
                    print("4. Account created successfully")
                    messagebox.showinfo(
                        "Welcome",
                        f"Welcome {username}! Your account has been created.",
                        parent=self.root
                    )
                    self.show_main_screen()
                    return
                    
                except Exception as e:
                    print(f"ERROR: Failed to create account: {e}")
                    self.error_label.config(text=f"Account creation failed: {str(e)}")
                    return
                    
            except Exception as e:
                print(f"ERROR: Dialog failed: {e}")
                self.error_label.config(text="Failed to create account")
                return
        
        # Handle existing user login
        try:
            print("\n=== Existing User Login Flow ===\n")
            # self.current_token = check_password(username, hashed_password)
            login_result = self.client.log_into_account(username, hashed_password)
            self.current_token = login_result[1]
            # self.current_user_id = user.userID
            self.current_user_id = self.get_userID_by_username(username)
            print("Login successful")
            self.show_main_screen()
            messagebox.showinfo(
                "Welcome Back",
                f"Welcome back, {username}!",
                parent=self.root
            )
        except AssertionError:
            print("ERROR: Invalid password")
            self.error_label.config(text="Invalid password")
        except Exception as e:
            print(f"ERROR: Login failed: {e}")
            self.error_label.config(text=f"Login failed: {str(e)}")
    
    def handle_signup(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
            
        try:
            hashed_password = self.client.hash_password(password)
            self.current_token = self.client.create_account(username, hashed_password)
            # TODO: translate to backend WP function
            self.current_user_id = self.get_userID_by_username(username)
            # user = user_trie.trie.get(username) # CHANGE THIS
            # self.current_user_id = user.uid # CHANGE THIS
            self.show_main_screen()
        except AssertionError:
            messagebox.showerror("Error", "Username already exists")
    
    def handle_logout(self):
        self.current_user_id = None
        self.current_token = None
        self.show_login_screen()
        
    def handle_delete_account(self):
        """Handle the deletion of the current user's account"""
        # Confirm deletion
        if not messagebox.askyesno(
            "Delete Account",
            "Are you sure you want to delete your account? This action cannot be undone.\n\n" +
            "This will:\n" +
            "- Delete all your messages (sent and received)\n" +
            "- Remove all your conversations\n" +
            "- Delete your account permanently",
            icon='warning'
        ):
            return

        self.client.delete_account(self.current_user_id, self.current_token)
        messagebox.showinfo("Success", "Your account has been deleted successfully.")
        self.handle_logout()  # Logout after deletion
        
        # TODO: (deletion error handling if needed?)
        # Delete the account
        # if delete_account(self.current_user_id):
            # messagebox.showinfo("Success", "Your account has been deleted successfully.")
            # self.handle_logout()  # Logout after deletion
        # else:
            # messagebox.showerror("Error", "Failed to delete account. Please try again.")
        
    def create_user_list(self):
        """Creates the left panel containing the list of online users"""
        # Frame for user list with fixed width
        users_frame = ttk.Frame(self.main_frame, width=200)
        users_frame.grid(row=1, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        users_frame.grid_propagate(False)  # Maintain fixed width
        
        # Label above user list
        ttk.Label(users_frame, text="Available Users", font=("Helvetica", 10, "bold")).grid(row=0, column=0, pady=5)
        
        # Listbox for users with scrollbar
        self.users_list = tk.Listbox(users_frame, selectmode=tk.SINGLE, font=("Helvetica", 10))
        users_scrollbar = ttk.Scrollbar(users_frame, orient=tk.VERTICAL, 
                                      command=self.users_list.yview)
        self.users_list.configure(yscrollcommand=users_scrollbar.set)
        
        # Bind selection event
        self.users_list.bind('<<ListboxSelect>>', self.on_user_select)
        
        # Grid the listbox and scrollbar
        self.users_list.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        users_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Selected user label
        self.selected_user_label = ttk.Label(users_frame, text="No user selected", font=("Helvetica", 9))
        self.selected_user_label.grid(row=2, column=0, pady=5)
        
        # Configure grid weights
        users_frame.columnconfigure(0, weight=1)
        users_frame.rowconfigure(1, weight=1)

    def create_message_area(self):
        """Creates the center panel containing the message history"""
        # Frame for messages
        messages_frame = ttk.Frame(self.main_frame)
        messages_frame.grid(row=1, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Message controls frame
        controls_frame = ttk.Frame(messages_frame)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Message action buttons
        ttk.Button(controls_frame, text="Delete Selected", command=self.delete_selected_messages).grid(row=0, column=0, padx=5)
        ttk.Button(controls_frame, text="Mark All as Read", command=self.mark_selected_as_read).grid(row=0, column=1, padx=5)
        
        # Label for messages
        ttk.Label(messages_frame, text="Messages", font=("Helvetica", 10, "bold")).grid(row=1, column=0, pady=5)
        
        # Listbox for messages with scrollbar
        self.messages_list = tk.Listbox(
            messages_frame,
            selectmode=tk.MULTIPLE,
            font=("Helvetica", 10),
            activestyle='none',  # Remove the active highlight
            height=20  # Make the listbox taller
        )
        messages_scrollbar = ttk.Scrollbar(messages_frame, orient=tk.VERTICAL,
                                         command=self.messages_list.yview)
        self.messages_list.configure(yscrollcommand=messages_scrollbar.set)
        
        # Bind click event to mark messages as read
        self.messages_list.bind('<<ListboxSelect>>', self.on_message_select)
        
        # Grid the listbox and scrollbar
        self.messages_list.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        messages_scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(2, weight=1)

    def create_input_area(self):
        """Creates the bottom panel containing the message input and send button"""
        # Frame for input area
        input_frame = ttk.Frame(self.main_frame)
        input_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Message entry field
        self.message_entry = ttk.Entry(input_frame, font=("Helvetica", 10))
        self.message_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        # Send button
        self.send_button = ttk.Button(input_frame, text="Send",
                                    command=self.send_message)
        self.send_button.grid(row=0, column=1, sticky=(tk.E), padx=5)
        
        # Configure grid weights
        input_frame.columnconfigure(0, weight=1)
        
        # Bind Enter key to send message
        self.message_entry.bind("<Return>", lambda e: self.send_message())
    def handle_signup(self):
        """Handle signup button click"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            self.error_label.config(text="Please enter both username and password")
            return
        
        try:
            # Hash the password and create account
            hashed_password = self.client.hash_password(password)
            # TODO: why don't we track session token here
            # self.client.create_account(username, hashed_password)
            
            # Auto-login after successful signup
            self.handle_login()
        except AssertionError:
            self.error_label.config(text="Username already exists")
        except Exception as e:
            self.error_label.config(text=str(e))
    
    def handle_logout(self):
        """Handle logout button click"""
        self.current_user_id = None
        self.current_token = None
        self.show_login_screen()
    
    def refresh_user_list(self):
        """Refresh the list of available users"""
        print("\n=== Refreshing user list... ===\n")
        try:
            # Store current selection if any
            current_selection = None
            selected_indices = self.users_list.curselection()
            if selected_indices:
                current_selection = self.users_list.get(selected_indices[0])
                if '[NEW]' in current_selection:
                    current_selection = current_selection.replace('[NEW] ', '')
                if ' (UNREAD:' in current_selection:
                    current_selection = current_selection.split(' (UNREAD:')[0]
            
            print("1. Clearing user list...")
            self.users_list.delete(0, tk.END)
            
            print("2. Getting current username...")
            current_username = self.get_username_by_id(self.current_user_id)
            # TODO: 
            # current_user = user_base.users.get(self.current_user_id)
            # current_userID = self.get_userID_by_username(current_username)
            print(f"Current username: {current_username}")
            
            print("3. Getting all users...")
            # users = list_accounts("*")
            users = self.client.list_accounts(self.current_user_id, self.current_token, "*")
            print(f"Found {len(users)} users: {users}")
            
            # Get users with unread messages first
            unread_users = set()
            unread_counts = {}
            
            # Count unread messages per sender
            # c[0]: message UID, c[1]: sender ID, c[2]: receiver ID
            current_unread_messages = self.client.get_unread_messages(self.current_user_id, self.current_token)
            for c in current_unread_messages:
                curr_msg = self.client.get_message_info(self.current_user_id, self.current_token, c[0])
                if curr_msg[0]:
                    sender_username = self.get_username_by_id(c[1])
                    if sender_username:
                        unread_users.add(sender_username)
                        unread_counts[sender_username] = unread_counts.get(sender_username, 0) + 1
                        
            # for msg_id in current_user.unread_messages:
                # msg = message_base.messages.get(msg_id)
                # if msg:
                    # sender_username = self.get_username_by_id(msg.sender_id)
                    # if sender_username:
                        # unread_users.add(sender_username)
                        # unread_counts[sender_username] = unread_counts.get(sender_username, 0) + 1
            
            # Add users with unread messages at the top
            if unread_users:
                self.users_list.insert(tk.END, "━━━ Unread Messages ━━━")
                for username in sorted(unread_users):
                    if username != current_username:
                        display_text = f"[NEW] {username} (UNREAD: {unread_counts[username]})"
                        self.users_list.insert(tk.END, display_text)
                        self.users_list.itemconfig(tk.END, fg='red')
                
                # Add separator
                self.users_list.insert(tk.END, "━━━━━━━━━━━━━━━━━━━")
            
            # Add other users
            for username in sorted(users):
                if username != current_username and username not in unread_users:
                    self.users_list.insert(tk.END, username)
            
            # Restore selection if it still exists
            if current_selection:
                for i in range(self.users_list.size()):
                    item = self.users_list.get(i)
                    clean_item = item.replace('[NEW] ', '').split(' (UNREAD:')[0]
                    if clean_item == current_selection:
                        self.users_list.selection_set(i)
                        self.users_list.see(i)  # Ensure the selected item is visible
                        break
            
            print("\n=== User list refresh complete ===\n")
        except Exception as e:
            print(f"\n!!! Error refreshing user list: {str(e)} !!!\n")
            import traceback
            traceback.print_exc()
    
    def send_message(self):
        """Send a message to the selected user"""
        message = self.message_entry.get().strip()
        if not message:
            return
        
        # Get selected recipient
        selection = self.users_list.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a recipient")
            return
        
        recipient_text = self.users_list.get(selection[0])
        if '━' in recipient_text:  # Skip if separator selected
            messagebox.showerror("Error", "Please select a valid user")
            return
            
        # Remove [NEW] prefix and unread count if present
        recipient_username = recipient_text.replace('[NEW] ', '').split(' (UNREAD:')[0]
        recipient_id = self.get_userID_by_username(recipient_username)
        if not recipient_id:
            messagebox.showerror("Error", "Recipient does not exist")
            return

        # Send message
        try:
            print(f"\n=== Sending Message ===")
            print(f"[DEBUG] From user: {self.current_user_id} to user: {recipient_id}")
            print(f"[DEBUG] Message content: {message}")
            
            # Try to send message
            success = self.client.send_message(self.current_user_id, self.current_token, recipient_id, message)
            if not success:
                print("[ERROR] Failed to send message - server returned error")
                messagebox.showerror("Error", "Failed to send message. Please try again.")
                return
                
            print("[DEBUG] Message sent successfully")
            
            # Clear message entry
            self.message_entry.delete(0, tk.END)
            
            # Update UI
            print("[DEBUG] Updating UI...")
            self.display_messages(mark_as_read=True)  # Show sent message
            self.refresh_user_list()
            self.update_unread_count()
            
            # Schedule a delayed refresh to catch any updates
            def delayed_refresh():
                print("\n=== Running Delayed Refresh ===")
                try:
                    self.refresh_user_list()
                    self.update_unread_count()
                    self.display_messages(mark_as_read=True)
                    print("=== Delayed Refresh Complete ===\n")
                except Exception as e:
                    print(f"[ERROR] Error in delayed refresh: {str(e)}")
            
            print("[DEBUG] Scheduling delayed refresh...")
            self.root.after(1000, delayed_refresh)
            
            print("=== Message Send Complete ===\n")
            
        except Exception as e:
            print(f"[ERROR] Failed to send message: {str(e)}")
            messagebox.showerror("Error", "Failed to send message - connection error")
    
        # Send the message
        # if send_message(self.current_user_id, recipient_id, message):
            # self.message_entry.delete(0, tk.END)
            # self.display_messages()
        # else:
            # messagebox.showerror("Error", "Failed to send message")
    
    def display_messages(self, mark_as_read=False):
        """Read and display messages"""
        print("\n=== Refreshing Messages ===")
        self.messages_list.delete(0, tk.END)
        self.message_ids.clear()
        
        # Get selected user
        selection = self.users_list.curselection()
        if not selection:
            print("[DEBUG] No user selected")
            self.messages_list.insert(tk.END, "Select a user to view messages")
            return
            
        selected_text = self.users_list.get(selection[0])
        if '━' in selected_text:  # Skip if separator selected
            print("[DEBUG] Separator selected, skipping")
            return
            
        # Extract username from display text
        selected_username = selected_text.split(' (UNREAD:')[0] if ' (UNREAD:' in selected_text else selected_text
        print(f"[DEBUG] Selected username: {selected_username}")
        
        selected_userID = self.get_userID_by_username(selected_username)
        if not selected_userID:
            print(f"[ERROR] Could not get user ID for username: {selected_username}")
            return
        
        print(f"[DEBUG] Getting conversation between user {self.current_user_id} and user {selected_userID}")
        
        try:
            # Get conversation
            curr_conversation = self.client.display_conversation(self.current_user_id, self.current_token, selected_userID)
            
            if not curr_conversation:
                print("[DEBUG] No messages in conversation")
                self.messages_list.insert(tk.END, f"No messages with {selected_username} yet")
                return
            
            print(f"[DEBUG] Found {len(curr_conversation)} messages")
            
            # Separate unread and read messages
            unread_messages = []
            read_messages = []
            
            for conv_msg in curr_conversation:
                try:
                    msg_id, content, is_sender = conv_msg
                    print(f"[DEBUG] Processing message {msg_id}: sender={is_sender}, content={content}")
                    
                    if is_sender:
                        # Message sent by current user
                        read_messages.append((conv_msg, f"You: {content}"))
                        print(f"[DEBUG] Added sent message {msg_id} to read messages")
                    else:
                        # Message received from other user
                        message_info = self.client.get_message_info(self.current_user_id, self.current_token, msg_id)
                        print(f"[DEBUG] Message info for {msg_id}: {message_info}")
                        
                        if message_info and len(message_info) >= 1:
                            has_been_read = message_info[0]
                            if not has_been_read:
                                unread_messages.append((conv_msg, f"{selected_username}: {content}"))
                                print(f"[DEBUG] Added unread message {msg_id}")
                                if mark_as_read:
                                    print(f"[DEBUG] Marking message {msg_id} as read")
                                    self.client.mark_message_as_read(self.current_user_id, self.current_token, msg_id)
                                    self.client.read_messages(self.current_user_id, self.current_token, 1)
                            else:
                                read_messages.append((conv_msg, f"{selected_username}: {content}"))
                                print(f"[DEBUG] Added read message {msg_id}")
                        else:
                            print(f"[WARN] No message info for {msg_id}, treating as read")
                            read_messages.append((conv_msg, f"{selected_username}: {content}"))
                except Exception as e:
                    print(f"[ERROR] Error processing message {conv_msg}: {str(e)}")
                    continue
                    
            print(f"[DEBUG] Found {len(unread_messages)} unread and {len(read_messages)} read messages")
            
        except Exception as e:
            print(f"[ERROR] Failed to get conversation: {str(e)}")
            self.messages_list.insert(tk.END, "Error loading messages")
            return
                # Only show messages section if we have messages
        if unread_messages or read_messages:
            # Display unread messages first if any exist
            if unread_messages:
                print("[DEBUG] Displaying unread messages")
                self.messages_list.insert(tk.END, "━━━ Unread Messages ━━━")
                for conv_msg, text in unread_messages:
                    self.messages_list.insert(tk.END, text)
                    self.message_ids.append(conv_msg[0])
                    self.messages_list.itemconfig(tk.END, fg='red')
                    print(f"[DEBUG] Displayed unread message: {text}")
                
                # Only add separator if there are read messages to follow
                if read_messages:
                    self.messages_list.insert(tk.END, "━━━━━━━━━━━━━━━━━━━")
                    self.messages_list.insert(tk.END, "━━━ Read Messages ━━━")
            
            # Display read messages
            if read_messages:
                for conv_msg, text in read_messages:
                    self.messages_list.insert(tk.END, text)
                    self.message_ids.append(conv_msg[0])
                    self.messages_list.itemconfig(tk.END, fg='white')  # Ensure read messages are white
                print(f"[DEBUG] Displayed {len(read_messages)} read messages")
        
        # Scroll to show unread messages if any, otherwise scroll to bottom
        if unread_messages and not mark_as_read:
            self.messages_list.see(0)
        else:
            self.messages_list.see(tk.END)
    
    def delete_selected_messages(self):
        """Delete selected messages"""
        selection = self.messages_list.curselection()
        if not selection:
            messagebox.showinfo("No Messages Selected", "Please select one or more messages to delete.")
            return
            
        # Skip if separator is selected
        for index in selection:
            item_text = self.messages_list.get(index)
            if '━' in item_text:
                messagebox.showwarning("Invalid Selection", "Cannot delete separator lines. Please select only messages.")
                return
        
        # Confirm deletion
        msg = "Are you sure you want to delete the selected message(s)? This action cannot be undone."
        if len(selection) > 1:
            msg = f"Are you sure you want to delete {len(selection)} messages? This action cannot be undone."
            
        if not messagebox.askyesno("Confirm Delete", msg, icon='warning'):
            return
            
        # Delete selected messages
        deleted_count = 0
        for index in reversed(selection):
            message_id = self.message_ids[index]
            # if delete_message(message_id):  # Removed current_user_id parameter
            self.client.delete_message(self.current_user_id, message_id, self.current_token)
            self.messages_list.delete(index)
            del self.message_ids[index]
            deleted_count += 1
        
        # Update the display
        self.refresh_user_list()
        self.update_unread_count()
        
        # Show success message
        if deleted_count > 0:
            msg = f"Successfully deleted {deleted_count} message{'s' if deleted_count > 1 else ''}."
            messagebox.showinfo("Success", msg)
    
    def mark_selected_as_read(self):
        """Mark all messages from the selected user as read"""
        # Get selected user
        user_selection = self.users_list.curselection()
        if not user_selection:
            messagebox.showerror("Error", "Please select a user to mark messages as read")
            return
            
        selected_text = self.users_list.get(user_selection[0])
        if '━' in selected_text:  # Skip if separator selected
            messagebox.showerror("Error", "Please select a valid user")
            return
            
        # Extract username from the selected text (handle both normal and unread message formats)
        if '(UNREAD:' in selected_text:
            username = selected_text.split(' (UNREAD:')[0].replace('[NEW] ', '')
        else:
            username = selected_text
            
        try:
            marked_count = 0
            print(f"\n=== Marking All Messages from {username} as Read ===")
            
            # Get all unread messages
            unread_messages = self.client.get_unread_messages(self.current_user_id, self.current_token)
            if not unread_messages:
                messagebox.showinfo("Info", "No unread messages from this user")
                return
                
            # Get the sender's user ID
            sender_id = self.get_userID_by_username(username)
            if not sender_id:
                messagebox.showerror("Error", "Could not find the selected user")
                return
                
            # Mark all unread messages from this sender as read
            for msg in unread_messages:
                # msg[0] is message_uid, msg[1] is sender_id
                if msg[1] == sender_id:
                    print(f"[DEBUG] Marking message {msg[0]} as read")
                    self.client.mark_message_as_read(self.current_user_id, self.current_token, msg[0])
                    marked_count += 1
                    print(f"[DEBUG] Successfully marked message {msg[0]} as read")
            
            print(f"[DEBUG] Marked {marked_count} messages as read")
            
            if marked_count > 0:
                # Update the unread count and refresh the display
                self.refresh_user_list()
                self.update_unread_count()
                self.display_messages()
                
                # Show success message
                messagebox.showinfo("Success", f"Marked {marked_count} messages from {username} as read")
            
            print("=== Mark as Read Complete ===\n")
            
        except Exception as e:
            print(f"[ERROR] Failed to mark messages as read: {str(e)}")
            messagebox.showerror("Error", "Failed to mark messages as read")
            
    def on_message_select(self, event):
        """Handle message selection"""
        selection = self.messages_list.curselection()
        if not selection:
            return
        # Update UI for selected messages
        for index in selection:
            item_text = self.messages_list.get(index)
            if '━' not in item_text:  # Skip separators
                self.messages_list.itemconfig(index, fg='white')
    
    def on_user_select(self, event):
        """Handle user selection from the list"""
        selection = self.users_list.curselection()
        if not selection:
            self.selected_user_label.config(text="No user selected")
            return
            
        # Get selected item text and extract username
        selected_text = self.users_list.get(selection[0])
        
        # Skip if separator line is selected
        if '━' in selected_text:
            self.users_list.selection_clear(0, tk.END)
            return
            
        # If user has unread messages, mark them as read
        if '(MESSAGES:' in selected_text:
            username = selected_text.split(' (MESSAGES:')[0]
            # selected_user = get_user_by_username(username)
            selected_userID = self.get_userID_by_username(username)
            if selected_userID:
                # Display messages with mark_as_read=True to mark them as read
                self.display_messages(mark_as_read=True)
                # Refresh the user list to move the user to the regular section
                self.refresh_user_list()
                # Re-select the user in the regular section
                for i in range(self.users_list.size()):
                    if self.users_list.get(i) == username:
                        self.users_list.selection_clear(0, tk.END)
                        self.users_list.selection_set(i)
                        self.users_list.see(i)
                        break
            
        # Extract username from display text (remove message count if present)
        selected_username = selected_text.split(' (MESSAGES:')[0]
        
        # If this is a different user than before, mark previous messages as read
        if hasattr(self, 'previous_selected_user') and self.previous_selected_user != selected_username:
            self.display_messages(mark_as_read=False)  # Mark previous conversation as read
        
        self.previous_selected_user = selected_username
        self.selected_user_label.config(text=f"Selected: {selected_username}")
        
        # Update message display to show conversation with selected user
        self.display_messages(mark_as_read=False)
    
    def run(self):
        """Start the main event loop"""
        # Create test users
        # test_users = [
            # ("alice", "test123"),
            # ("bob", "test123"),
            # ("charlie", "test123"),
            # ("david", "test123"),
            # ("eve", "test123")
        # ]
        
        # Create test account users
        # for username, password in test_users:
            # try:
                # if not self.client.search_username(username): 
                    # create_account(username, self.client.hash_password(password))
                    # self.client.create_account(username, self.client.hash_password(password))
            # except Exception as e:
                # print(f"Error creating user {username}: {e}")
        
        # Print test accounts
        # print("Test accounts created:")
        # for username, password in test_users:
            # print(f"Username: {username}, Password: {password}")
        
        # Start the main loop
        self.root.mainloop()

    def update_unread_count(self):
        """Update the unread message counter"""
        if not hasattr(self, 'unread_counter_label') or not self.current_user_id:
            print("[DEBUG] update_unread_count: Missing label or user ID")
            return
            
        print(f"\n=== Updating Unread Count for User {self.current_user_id} ===")
        # Get unread messages for current user
        unread_messages = self.client.get_unread_messages(self.current_user_id, self.current_token)
        print(f"[DEBUG] Raw unread messages: {unread_messages}")
        
        # Group messages by sender
        sender_counts = {}
        if unread_messages:
            for msg in unread_messages:
                sender_id = msg[1]  # msg[1] is sender_id
                sender_name = self.get_username_by_id(sender_id)
                sender_counts[sender_name] = sender_counts.get(sender_name, 0) + 1
            print(f"[DEBUG] Unread messages per sender: {sender_counts}")
        
        unread_count = len(unread_messages) if unread_messages else 0
        print(f"[DEBUG] Total unread count: {unread_count}")
        self.unread_counter_label.config(text=f"Unread Messages: {unread_count}")
        print("=== Unread Count Update Complete ===\n")

if __name__ == "__main__":
    # Create and run the chat interface
    if len(sys.argv) != 3:
        print_usage()
        
    host = sys.argv[1]
    port = sys.argv[2]
    
    try:
        port = int(port)
        if port < 1 or port > 65535:
            raise ValueError("Port must be between 1 and 65535")
    except ValueError as e:
        print(f"Error: Invalid port number - {str(e)}")
        print_usage()
    
    # Create and run the chat interface
    try:
        chat = ChatInterface(host, port)
        chat.run()
    except Exception as e:
        print(f"Failed to start chat application: {str(e)}")
        sys.exit(1)
