import sqlite3
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os
from datetime import date,timedelta
load_dotenv()
import logging
from pathlib import Path
logs_folder = Path('logs')
logs_folder.mkdir(exist_ok=True)
logging.basicConfig(filename=logs_folder/'harare_fresh.log',level=logging.INFO,format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)
base_folder = Path(__file__).resolve().parent
database_file = base_folder/'harare_fresh.db'
reports_folder = base_folder/'reports'
management_reports = reports_folder/'management'
customer_reports = reports_folder/'customers'
management_reports.mkdir(parents=True,exist_ok=True)
customer_reports.mkdir(parents=True,exist_ok=True)
connection = sqlite3.connect(database_file)
connection.execute('PRAGMA foreign_keys = ON')
cursor = connection.cursor()
valid_order_statuses = ['pending','delivery_otw','delivered','cancelled','completed']
connection.commit()
def add_customer(connection,name,email,phone):
    try:
        cursor = connection.cursor()
        cursor.execute('INSERT INTO customers (customer_name,customer_email,phone) VALUES(?,?,?)',(name,email,phone))
        connection.commit()
        print(f'CUSTOMER CREATED SUCCESSFULLY!\nCustomer ID: {cursor.lastrowid}')
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        print('FAILED TO CREATE CUSTOMER')
        raise
def create_order(connection,customer_id):
    if not isinstance(customer_id,int) or customer_id <= 0:
        raise ValueError('Invalid customer ID')
    if not get_customer(connection,customer_id):
        raise ValueError('Customer does not exist')
    try:
        cursor = connection.cursor()
        cursor.execute('INSERT INTO orders (customer_id) VALUES (?)',(customer_id,))
        #print(f'ORDER CREATED SUCCESSFULLY!\nOrder ID: {cursor.lastrowid}')
        return cursor.lastrowid
    except Exception:
        print('FAILED TO CREATE ORDER!')
        raise
def get_order(connection,order_id):
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT order_id,customer_id,status,created_at FROM orders WHERE order_id = ?',(order_id,))
        info = cursor.fetchone()
        if info is None:
            return None
        return {'order_id':info[0],'customer_id':info[1],'status':info[2],'created_at':info[3]}
    except Exception:
        print(f'FAILED TO RETRIEVE ORDER')
        raise
def get_customer(connection,customer_id):
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT customer_id,customer_name,customer_email,phone FROM customers WHERE customer_id = ?',(customer_id,))
        info = cursor.fetchone()
        if info is None:
            return None
        return {'id':info[0],'name':info[1],'email':info[2],'phone':info[3]}
    except Exception:
        print(f'FAILED TO RETRIEVE CUSTOMER')
        raise
def add_order_item(connection,order_id,product_id,quantity):
    if not isinstance(order_id,int) or order_id <= 0:
        raise ValueError('Invalid order ID')
    if not isinstance(product_id,int) or product_id <= 0:
        raise ValueError('Invalid product ID')
    if not isinstance(quantity,int) or quantity <= 0:
        raise ValueError('Quantity must be a positive integer')
    order = get_order(connection,order_id)
    if not order:
        raise ValueError('Order does not exist')
    product = get_product(connection,product_id)
    if not product:
        raise ValueError('Product does not exist')
    check_stock(connection,product_id,quantity)
    try:
        cursor = connection.cursor()
        cursor.execute('INSERT INTO order_items (order_id,product_id,quantity,unit_price,total_amount) VALUES(?,?,?,?,?)',(order_id,product_id,quantity,product['unit_price'],product['unit_price'] * quantity))
        reduce_stock(connection,product_id,quantity)
        #print('Order item added successfully')
        return cursor.lastrowid
    except Exception:
        print('Failed to add order item')
        raise
def get_customer_orders(connection,customer_id):
    cursor = connection.cursor()
    try:
        cursor.execute('''SELECT orders.order_id,products.product_name,order_items.quantity,order_items.unit_price,order_items.total_amount,orders.status FROM orders JOIN order_items ON orders.order_id = order_items.order_id JOIN products ON order_items.product_id = products.product_id WHERE orders.customer_id = ?ORDER BY orders.created_at DESC''',(customer_id,))
        info = cursor.fetchall()
        orders = []
        for order in info:
            orders.append({'order_id': order[0],'product': order[1],'quantity': order[2],'unit_price': order[3],'total_amount': order[4],'status': order[5]})
        return orders
    except Exception:
        print('Failed to retrieve customer orders')
        raise
def get_customer_summary(connection,customer_id):
    cursor = connection.cursor()
    try:
        cursor.execute('''SELECT COUNT(DISTINCT orders.order_id),COALESCE(SUM(order_items.total_amount),0),COALESCE(SUM(order_items.total_amount) * 1.0 /NULLIF(COUNT(DISTINCT orders.order_id),0),0) FROM orders LEFT JOIN order_items ON orders.order_id = order_items.order_id WHERE orders.customer_id = ?''',(customer_id,))
        info = cursor.fetchone()
        return {'total_orders':info[0],'total_spent':info[1],'average_order':info[2]}
    except Exception:
        print('FAILED TO GET CUSTOMER SUMMARY')
        raise
def get_customer_profile(connection,customer_id):
    cursor = connection.cursor()
    customer = get_customer(connection,customer_id)
    if customer is None:
        return None
    orders = get_customer_orders(connection,customer_id)
    summary = get_customer_summary(connection,customer_id)
    return {'customer':customer,'summary':summary,'orders':orders}
def get_sales_summary(connection,start_date,end_date):
    try:
        cursor = connection.cursor()
        cursor.execute('''SELECT COUNT(DISTINCT orders.order_id),COALESCE(SUM(order_items.total_amount),0),COALESCE(SUM(order_items.total_amount) * 1.0 /NULLIF(COUNT(DISTINCT orders.order_id),0),0),COUNT(DISTINCT orders.customer_id) FROM orders LEFT JOIN order_items ON orders.order_id = order_items.order_id WHERE orders.created_at >= ? AND orders.created_at < ?''',(start_date,end_date))
        info = cursor.fetchone()
        return {'total_orders': info[0],'total_sales': info[1],'average_order_value': info[2],'unique_customers': info[3]}
    except Exception:
        print('Operation failed!!')
        raise
def get_product_sales(connection,start_date,end_date):
    try:
        cursor = connection.cursor()
        cursor.execute('''SELECT products.product_name,COALESCE(SUM(order_items.quantity),0),COUNT(DISTINCT order_items.order_id),COALESCE(SUM(order_items.total_amount),0) FROM order_items JOIN orders ON order_items.order_id = orders.order_id JOIN products ON order_items.product_id = products.product_id WHERE orders.created_at >= ? AND orders.created_at < ? GROUP BY products.product_id, products.product_name ORDER BY SUM(order_items.total_amount) DESC''',(start_date,end_date))
        info = cursor.fetchall()
        products = []
        for i in info:
            products.append({'product': i[0],'units_sold': i[1],'orders': i[2],'sales': i[3]})
        return products
    except Exception:
        print('OPERATION FAILED')
        raise
def get_management_report(connection,start_date,end_date):
    sales_summary = get_sales_summary(connection,start_date,end_date)
    product_sales = get_product_sales(connection,start_date,end_date)
    return {'period':{'start_date':start_date,'end_date':end_date},'sales_summary':sales_summary,'product_sales':product_sales}
def generate_report_pdf(report,filename):
    doc = SimpleDocTemplate(str(filename))
    styles = getSampleStyleSheet()
    story =[]
    data =[['Product','Units Sold','Orders','Sales','% of Sales']]
    total_sales = report['sales_summary']['total_sales']
    for product in report['product_sales']:
        sales_percentage = (product['sales']/total_sales *100 if total_sales > 0 else 0)
        data.append([product['product'],product['units_sold'],product['orders'],product['sales'],round(sales_percentage,2)])
    table = Table(data,repeatRows=1)
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),1,colors.black),('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ALIGN',(1,1),(-1,-1),'RIGHT'),('ALIGN',(0,0),(-1,0),'CENTRE'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story.append(Paragraph('HARARE FRESH DISTRIBUTORS',styles['Title']))
    story.append(Paragraph(f'Reporting period: {report['period']['start_date']} to {report['period']['end_date']}',styles['Heading1']))
    story.append(Spacer(1,12))
    story.append(Paragraph(f"Total Orders: {report['sales_summary']['total_orders']}<br/>Total Sales: ${report['sales_summary']['total_sales']:.2f}<br/>Average order value: ${report['sales_summary']['average_order_value']:.2f}<br/>Unique customers: {report['sales_summary']['unique_customers']}",styles['Normal']))
    story.append(Spacer(1,12))
    story.append(table)
    doc.build(story)
def generate_customer_report_pdf(profile,filename):
    doc = SimpleDocTemplate(str(filename))
    styles = getSampleStyleSheet()
    story =[]
    story.append(Paragraph('HARARE FRESH DISTRIBUTORS',styles['Title']))
    story.append(Paragraph('Customer Report',styles['Heading1']))
    story.append(Spacer(1,12))
    story.append(Paragraph(f'Customer: {profile['customer']['name']} <br/>Email: {profile['customer']['email']}<br/>Phone: {profile['customer']['phone']}'))
    story.append(Spacer(1,12))
    story.append(Paragraph('Customer Summary',styles['Heading1']))
    story.append(Paragraph(f'Total orders: {profile['summary']['total_orders']}<br/>Total spent: {profile['summary']['total_spent']}<br/>Average order value: {profile['summary']['average_order']}'))
    story.append(Spacer(1,12))
    story.append(Paragraph('Order History',styles['Heading1']))
    data = [['Order ID','Product','Quantity','Unit Price','Total','Status']]
    for order in profile['orders']:
        data.append([order['order_id'],order['product'],order['quantity'],order['unit_price'],order['total_amount'],order['status']])
    table = Table(data,repeatRows=1)
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),1,colors.black),('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ALIGN',(1,1),(-1,-1),'RIGHT'),('ALIGN',(0,0),(-1,0),'CENTRE'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story.append(table)
    doc.build(story)
def send_report_email(sender_email,sender_password,recipient_email,pdf_filename):
    try:
        message = EmailMessage()
        message['Subject'] ='Harare Fresh Report'
        message['To'] = recipient_email
        message['From'] = sender_email
        message.set_content(f'Please find the attached Harare Fresh Management Report')
        with open(pdf_filename,'rb') as file:
            pdf_data = file.read()
            message.add_attachment(pdf_data,maintype='application',subtype='pdf',filename=pdf_filename.name)
        with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
            smtp.login(sender_email,sender_password)
            smtp.send_message(message)
        print('Email sent successfully')
        return True
    except Exception:
        print('Failed to send email')
        raise
def run_management_report(connection,sender_email,sender_password,recipient_email):
    try:
        today = date.today()
        start_date = today - timedelta(days=7)
        start_date = start_date.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        report = get_management_report(connection,start_date,end_date)
        filename = management_reports/f'harare_fresh_report_{start_date}.pdf'
        generate_report_pdf(report,filename)
        logger.info(f'Management report generated: {filename}')
        send_report_email(sender_email,sender_password,recipient_email,filename)
        logger.info(f'Management report emailed successfully: {filename}')
        print('MANAGEMENT REPORT WORKFLOW COMPLETED SUCCESSFULLY!!')
        return True
    except Exception:
        logger.exception('Management report workflow failed!')
        raise
def generate_customer_report(connection,customer_id):
    try:
        profile = get_customer_profile(connection,customer_id)
        if profile is None:
            print('Customer not found')
            return None
        filename =customer_reports/f"{profile['customer']['name']}'s report.pdf"
        generate_customer_report_pdf(profile,filename)
        logger.info(f"{profile['customer']['name']}'s report successfully generated")
        return filename
    except Exception:
        logger.exception('Could not generate report')
        raise
def get_customers(connection):
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT customer_id,customer_name FROM customers')
        customers = cursor.fetchall()
        customer_list =[]
        for customer in customers:
            customer_list.append({'id':customer[0],'customer_name':customer[1]})
        return customer_list
    except Exception:
        print(f'FAILED TO RETRIEVE CUSTOMERS')
        raise
def management_menu(connection):
    while True:
        print('\n========== HARARE FRESH ==========')
        print('1. Customer Reports\n2. Sales Overview\n3. Create Order\n4. Manage Order\n5. Exit')
        choice = input('Select an option: ').strip()
        if choice == '1':
            customers = get_customers(connection)
            if not customers:
                print('No customers found')
                continue
            print('Available customers:')
            for i,customer in enumerate(customers,1):
                print(f'{i}. {customer['customer_name']}')
            try:
                position = int(input('Select customer: '))
            except ValueError:
                print('Please enter a valid number')
                continue
            if position < 1 or position > len(customers):
                print('Invalid customer selection')
                continue
            customer_id = customers[position-1]['id']
            report = generate_customer_report(connection,customer_id)
            if report:
                print(f'Report ready: {report}')
        elif choice == '2':
            print(sales_overview(connection))
        elif choice == '3':
            customers = get_customers(connection)
            print('Available customers:')
            for i,customer in enumerate(customers,1):
                print(f'{i}. {customer['customer_name']}')
            try:
                position = int(input('Select customer: '))
            except ValueError:
                print('Please enter a valid number')
                continue
            if position < 1 or position > len(customers):
                print('Invalid customer selection')
                continue
            customer_id = customers[position-1]['id']
            items = []
            while True:
                try:
                    product_id = int(input('Enter product ID: '))
                    quantity = int(input('Enter quantity: '))
                except ValueError:
                    print('Please enter valid inputs')
                    continue
                items.append((product_id,quantity))
                while True:
                    another = input('Add another product? (y/n): ').strip().lower()
                    if another == 'y':
                        break
                    if another == 'n':
                        break
                    print('Please enter y/n')
                if another =='n':
                    break
            order_id = create_full_order(connection,customer_id,items)
            print(display_order(connection,order_id))
            #if order_id:
                #print(f'ORDER CREATED SUCCESSFULLY\nOrder ID: {order_id}')
        elif choice == '4':
            try:
                order_id = int(input('Enter Order ID: '))
            except ValueError:
                print('Enter valid ID')
                continue
            display_order(connection,order_id)
            order_options = get_available_order_actions(connection,order_id)
            if not order_options:
                print('No further actions available')
            else:
                print('Available actions')
                for i,action in enumerate(order_options,1):
                    print(f'{i}. {action}')
                try:
                    selection = int(input('Select option: '))
                except ValueError:
                    print('Please select valid option')
                    continue
                if selection < 1 or selection > len(order_options):
                    print('Invalid option')
                    continue
                action = order_options[selection - 1]
                if action == 'cancelled':
                    cancel_order(connection,order_id)
                else:
                    update_order_status(connection,order_id,action)
                print('\nUpdated Order:')
                print(display_order(connection,order_id))
                
                
        elif choice == '5':
                print('Goodbye!')
                break
        else:
                print('Invalid option. Please try again.')
def sales_overview(connection):
    today = date.today()
    start_date = today - timedelta(days=7)
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    product_sales = get_product_sales(connection,start_date,end_date)
    sales_summary = get_sales_summary(connection,start_date,end_date)
    overview = 'SALES OVERVIEW'.center(30,'=') + '\n\n' + 'Period: Last 7 days' + '\n\n'
    overview += f'Total orders: {sales_summary['total_orders']}\nTotal Sales: ${sales_summary['total_sales']:.2f}\nAverage order: ${sales_summary['average_order_value']:.2f}\nUnique customers: {sales_summary['unique_customers']}\n\n'
    overview += 'PRODUCT PERFORMANCE'.center(30,'=') + '\n\n'
    overview += 'Product'.center(15,' ') + '|' + 'Units Sold'.center(10,' ') + '|' + 'Orders'.center(10,' ') + '|' + 'Sales'.center(10,' ') + '\n' + '-'*45
    for product in product_sales:
        overview += '\n' + f"{product['product']}"[:15].center(15,' ') + '|' + f"{product['units_sold']}".center(10,' ') + '|' + f"{product['orders']}".center(10,' ') + '|' + f"{product['sales']}".center(10,' ') 
    return overview
def add_product(connection,product_name,unit_price,stock_quantity):
    if not isinstance(product_name,str) or not product_name.strip():
        raise ValueError('Product name must not be empty')
    if not isinstance(unit_price,(float,int)) or unit_price <= 0  :
        raise ValueError('Unit price must be a positive number')
    if not isinstance(stock_quantity,int) or stock_quantity < 0:
        raise ValueError('Stock quantity must be a non-negative integer')
    try:
        cursor = connection.cursor()
        cursor.execute('INSERT INTO products (product_name,unit_price,stock_quantity) VALUES(?,?,?)',(product_name.strip(),unit_price,stock_quantity))
        connection.commit()
        print(f'PRODUCT ADDED SUCCESSFULLY!\nPRODUCT ID: {cursor.lastrowid}')
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        print('FAILED TO ADD PRODUCT')
        raise
def get_products(connection):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT product_id,product_name,unit_price,stock_quantity,status FROM products')
        products = cursor.fetchall()
        product_list =[]
        for product in products:
            product_list.append({'product_id':product[0],'product_name':product[1],'unit_price':product[2],'stock_quantity':product[3],'status':product[4]})
        return product_list
    except Exception:
        print(f'FAILED TO RETRIEVE PRODUCTS')
        raise
def get_product(connection,product_id):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT product_id,product_name,unit_price,stock_quantity,status FROM products WHERE product_id = ?',(product_id,))
        info = cursor.fetchone()
        if info is None:
            return None
        return {'product_id':info[0],'product_name':info[1],'unit_price':info[2],'stock_quantity':info[3],'status':info[4]}
    except Exception:
        print(f'FAILED TO RETRIEVE PRODUCT')
        raise
def check_stock(connection,product_id,quantity):
    if not isinstance(quantity,int) or quantity <= 0:
        raise ValueError('Quantity must be a positive integer')
    product = get_product(connection,product_id)
    if not product:
        raise ValueError('Product does not exist')
    if quantity > product['stock_quantity']:
        raise ValueError('Quantity cannot exceed available stock')
    return True
def reduce_stock(connection,product_id,quantity):
    try:
            cursor = connection.cursor()
            product = get_product(connection,product_id)
            cursor.execute('UPDATE products SET stock_quantity = ? WHERE product_id = ?',(product['stock_quantity'] - quantity,product_id))
            #print(f'{product['product_name']} stock reduced from {product['stock_quantity']} to {product['stock_quantity'] - quantity}')
            return product['stock_quantity'] - quantity
    except Exception:
            print('Failed to update stock!!')
            raise
def get_order_items(connection,order_id):
    if not isinstance(order_id,int) or order_id <= 0:
        raise ValueError('Invalid Order ID')
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT order_items.order_item_id,products.product_id,products.product_name,order_items.quantity,order_items.unit_price,order_items.total_amount FROM order_items JOIN products ON order_items.product_id = products.product_id WHERE order_items.order_id = ?',(order_id,))
        info = cursor.fetchall()
        order_items = []
        for item in info:
            order_items.append({'order_item_id':item[0],'product_id':item[1],'product_name':item[2],'quantity':item[3],'unit_price':item[4],'total_amount':item[5]})
        return order_items
    except Exception:
        print('Failed to get order items')
        raise
def get_order_total(connection,order_id):
    if not isinstance(order_id,int) or order_id <= 0:
        raise ValueError('Invalid Order ID')
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT COALESCE(SUM(total_amount),0) FROM order_items WHERE order_id = ?',(order_id,))
        return cursor.fetchone()[0]
    except Exception:
        print('Failure to get order total')
        raise
def update_order_status(connection,order_id,new_status):
    if not isinstance(order_id,int) or order_id <= 0:
        raise ValueError('Invalid Order ID')
    if not get_order(connection,order_id):
        raise ValueError('Order does not exist')
    if new_status not in valid_order_statuses:
        raise ValueError('Invalid status entered')
    try:
        cursor = connection.cursor()
        cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?',(new_status,order_id))
        connection.commit()
        print('Status updated successfully')
        return new_status
    except Exception:
        connection.rollback()
        print('Failed to update status')
        raise
def cancel_order(connection,order_id):
    if not isinstance(order_id,int) or order_id <= 0:
        raise ValueError('Invalid Order ID')
    order=get_order(connection,order_id)
    if not order:
        raise ValueError('Order does not exist')
    if order['status'] in ['cancelled','delivered','completed']:
        raise ValueError("Order cannot be cancelled")
    try:
        cursor = connection.cursor()
        order_items = get_order_items(connection,order_id)
        for item in order_items:
            product = get_product(connection,item['product_id'])
            cursor.execute('UPDATE products SET stock_quantity = ? WHERE product_id = ?',(product['stock_quantity'] + item['quantity'],item['product_id']))
        cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?',('cancelled',order_id))
        connection.commit()
        print('Order cancelled successfully')
        return True
    except Exception:
        connection.rollback()
        print('Failed to cancel order')
        raise
def create_full_order(connection,customer_id,items):
    if not isinstance(customer_id,int) or customer_id <= 0:
        raise ValueError('Invalid Customer ID')
    if not get_customer(connection,customer_id):
        raise ValueError('Invalid Customer')
    try:
        order_id = create_order(connection,customer_id)
        for item in items:
            if not isinstance(item[0],int) or item[0] <= 0:
                raise ValueError('Invalid product ID')
            if not isinstance(item[1],int) or item[1] <= 0:
                raise ValueError('Quantity should be a positive integer')
            product = get_product(connection,item[0])
            if not product:
                raise ValueError('Product does not exist')
            check_stock(connection,item[0],item[1])
            add_order_item(connection,order_id,item[0],item[1])
        #print('Order successfully created')
        connection.commit()
        return order_id
    except Exception:
        print('Failed to create order')
        connection.rollback()
        raise
def display_order(connection,order_id):
    if not isinstance(order_id,int) or order_id <= 0:
        raise ValueError('Invalid Order ID')
    try:
        order = get_order(connection,order_id)
        if not order:
            raise ValueError('Order does not exist')
        order_items = get_order_items(connection,order_id)
        total = get_order_total(connection,order_id)
        display = f'ORDER #{order_id}'.center(34,'=') + f'\nCustomer: {get_customer(connection,order['customer_id'])['name']}'
        display += f'\nStatus: {order['status']}\n\n'
        display += 'Product'.center(15,' ') + 'Qty'.center(5,' ') + 'Price'.center(7,' ')+ 'Total'.center(7,' ') + '\n'
        for item in order_items:
            display += f'{item['product_name'][:15]}'.center(15,' ') + f'{item['quantity']}'.center(5,' ') + f'${item['unit_price']:.2f}'.center(7,' ') + f'{item['total_amount']:.2f}'.center(7,' ') + '\n'
        display += '\n\n' + '-'* 34 + '\nTOTAL:' + f'${total:.2f}'
        display += '\n' + "=" * 34
        print(display)
    except Exception:
        print('Failed to display order')
        raise
def get_available_order_actions(connection, order_id):
    if not isinstance(order_id, int) or order_id <= 0:
        raise ValueError('Invalid Order ID')
    order = get_order(connection, order_id)
    if not order:
        raise ValueError('Order does not exist')
    status = order['status']
    if status == 'pending':
        return ['delivery_otw', 'cancelled']
    if status == 'delivery_otw':
        return ['delivered']
    if status == 'delivered':
        return ['completed']
    if status in ('completed', 'cancelled'):
        return []
    raise ValueError('Unknown order status')
email_address = os.getenv('email_address')
email_password = os.getenv('password')
if not email_password or not email_address:
    raise ValueError('Email credentials are missing from .env')
