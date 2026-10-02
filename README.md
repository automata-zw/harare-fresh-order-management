Harare Fresh Distributors — Order Management System
A Python-based order management and reporting system built for Harare Fresh Distributors, a fictional food and beverage distribution business.
The system centralises customer records, products, inventory, orders, order processing, reporting, PDF generation, email delivery, and application logging.
🎯 Problem
Harare Fresh's sales process involves orders being taken through WhatsApp and manually transferred into spreadsheets.
This creates several operational problems:
• Duplicate or inconsistent customer records
• Manual order-entry errors
• Difficulty tracking inventory
• Limited visibility into order status
• Time-consuming sales reporting
• No centralised order history
• Manual preparation and distribution of management reports
This system provides a centralised database and workflow for managing these operations.
🚀 Features
Customer Management
• Add customers
• Retrieve customer information
• View customer order history
• Generate customer summaries
• Generate customer PDF reports
Product & Inventory Management
• Add products
• Store unit prices
• Track inventory quantities
• Validate available stock
• Automatically reduce stock when an order is created
• Restore stock when an order is cancelled
Order Management
• Create orders for customers
• Add multiple products to a single order
• Store the sale-time unit price
• Calculate order totals
• Display complete order information
• Track order status
• Cancel orders
• Automatically restore inventory when orders are cancelled
Order Status Workflow
pending │ ├──→ delivery_otw │ │ │ └──→ delivered │ │ │ └──→ completed │ └──→ cancelled
Completed and cancelled orders are terminal states.
Reporting
• Seven-day sales overview
• Total orders
• Total sales
• Average order value
• Unique customers
• Product sales performance
• Units sold by product
• Customer order history
• Management PDF reports
• Customer PDF reports
Email
• Send generated management reports through email
• Attach PDF reports automatically
• Uses Gmail SMTP
Logging
Application events and failures are recorded in:
logs/harare_fresh.log
🛠️ Technologies
• Python
• SQLite
• ReportLab
• python-dotenv
• SMTP / EmailMessage
• Logging
• pathlib
Architecture
The core database relationship is:
CUSTOMER │ └──→ ORDERS │ └──→ ORDER_ITEMS │ └──→ PRODUCTS
An order can contain multiple products through the order_items table.
The order_items table also stores the unit price at the time of purchase so historical orders are not affected if a product's current price changes.
📁 Project Structure
Harare_Fresh/ │ ├── harare_fresh.py ├── requirements.txt ├── .gitignore ├── .env │ ├── harare_fresh.db │ ├── logs/ │ └── harare_fresh.log │ └── reports/ ├── customers/ └── management/
Database files, reports, logs, and environment variables are excluded from version control through .gitignore.
⚙️ Setup
1. Clone the repository
git clone <repository-url> cd <repository-folder>
2. Create a virtual environment
python -m venv .venv
Activate it on Windows:
.venv\Scripts\activate
3. Install dependencies
pip install -r requirements.txt
4. Configure environment variables
Create a .env file in the project root:
email_address=your-email@gmail.com password=your-app-password
The email credentials are loaded from environment variables and should never be committed to GitHub.
5. Run the application
python harare_fresh.py
🖥️ Management Menu
The application provides a command-line management interface:
========== HARARE FRESH ========== 
1. Customer Reports 
2. Sales Overview 
3. Create Order 
4. Manage Order 
5. Exit
Customer Reports
Select a customer to generate a customer report containing:
• Customer details
• Order history
• Total orders
• Total spending
• Average order value
Sales Overview
Displays recent business performance including:
• Total orders
• Total sales
• Average order value
• Unique customers
• Product performance
Create Order
A manager can:
• Select a customer
• Add one or more products
• Specify quantities
• Validate available stock
• Create the order
• Automatically reduce inventory
Manage Order
Orders can be progressed through their permitted workflow:
pending → delivery_otw → delivered → completed
Pending orders can also be cancelled.
Cancelling an order restores the inventory associated with all order items.
🔐 Transaction Safety
Order creation is handled as a database transaction.
If an order contains multiple products and one of the products fails validation or does not have sufficient stock, the transaction is rolled back.
This prevents situations where:
• An order exists without all its items
• Only some inventory is deducted
• Partial orders remain in the database
The same principle is applied when cancelling orders and restoring inventory.
📊 Reporting
The system separates business data from reporting logic.
Sales data is calculated from:
orders + order_items + products
This allows the system to generate management-level information from the underlying transactional data.
Generated reports are stored locally under:
reports/management/ reports/customers/
📧 Email Reports
Management reports can be generated as PDF documents and automatically sent through Gmail SMTP.
The email workflow is:
Database ↓ Sales calculations ↓ Management report ↓ PDF generation ↓ Email attachment ↓ Recipient
🧪 Testing
The system has been tested through end-to-end scenarios including:
• Customer creation
• Multi-product order creation
• Stock deduction
• Invalid stock quantities
• Order status transitions
• Order cancellation
• Multi-product stock restoration
• Invalid cancellation attempts
• Customer report generation
• Sales reporting
• Management PDF generation
• Email report delivery
• Application error logging
• Transaction rollback scenarios
🔮 Future Improvements
Possible future development includes:
• Web-based management dashboard
• WhatsApp order integration
• Automated customer notifications
• Automated scheduled reports
• Sales-representative accounts
• Delivery tracking
• Low-stock alerts
• Role-based authentication
• REST API
• Cloud database deployment
• Integration with accounting systems
👨‍💻 Project
Project: Automata Project #001
System: Harare Fresh Distributors Order Management System
Built with: Python + SQLite
This project was built as a practical business automation system to demonstrate how software can replace repetitive manual business processes with a centralised, reliable workflow.