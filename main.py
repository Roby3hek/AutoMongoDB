import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta

USERS = {
    "reader": {"password": "1234", "role": "read"},
    "editor": {"password": "1234", "role": "edit"},
    "admin": {"password": "1234", "role": "admin"}
}

DEVELOPER_INFO = "Разработчик: Туманян Р.А.\nEmail: 2004.roben@gmail.com\n2025 год"

class LoginDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Логин:").grid(row=0)
        tk.Label(master, text="Пароль:").grid(row=1)
        self.e1 = tk.Entry(master)
        self.e2 = tk.Entry(master, show="*")
        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        return self.e1

    def apply(self):
        self.username = self.e1.get()
        self.password = self.e2.get()

class CarDealerApp:
    def __init__(self, root, user_role, relogin_callback):
        self.root = root
        self.user_role = user_role
        self.relogin_callback = relogin_callback
        self.root.title("Автодилер - Управление базой данных")
        self.root.geometry("950x650")

        # Подключение к MongoDB
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['car_dealer']
        self.cars = self.db['cars']
        self.clients = self.db['clients']
        self.sales = self.db['sales']

        # Вкладки
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.setup_cars_tab()
        self.setup_clients_tab()
        self.setup_sales_tab()
        self.setup_buttons()
        self.setup_menu()
        self.refresh_all()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="О программе", command=self.show_about)
        helpmenu.add_separator()
        helpmenu.add_command(label="Выйти", command=self.logout)
        menubar.add_cascade(label="Справка", menu=helpmenu)

        # --- Меню отчетов ---
        reports = tk.Menu(menubar, tearoff=0)
        reports.add_command(label="Продажи по маркам", command=self.report_sales_by_brand)
        reports.add_command(label="Выручка по типу оплаты", command=self.report_revenue_by_payment)
        reports.add_command(label="Средняя цена по цвету", command=self.report_avg_price_by_color)
        reports.add_separator()
        reports.add_command(label="Клиенты по ФИО", command=self.report_clients_by_name)
        reports.add_command(label="Продажи за месяц", command=self.report_sales_by_month)
        reports.add_command(label="Автомобили по цвету", command=self.report_cars_by_color)
        menubar.add_cascade(label="Отчёты", menu=reports)

    def show_about(self):
        messagebox.showinfo("О программе", f"Информационная система автодилера\n\n{DEVELOPER_INFO}")

    def logout(self):
        if messagebox.askyesno("Выход", "Вы действительно хотите выйти и сменить пользователя?"):
            self.root.destroy()
            self.relogin_callback()

    def show_report(self, title, columns, rows):
        win = tk.Toplevel(self.root)
        win.title(title)
        tree = ttk.Treeview(win, columns=columns, show='headings')
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=140)
        tree.pack(fill='both', expand=True)
        for row in rows:
            tree.insert('', 'end', values=row)
        tk.Button(win, text="Закрыть", command=win.destroy).pack(pady=5)

    # --- ОТЧЁТЫ (агрегация) ---
    def report_sales_by_brand(self):
        result = list(self.sales.aggregate([
            {"$lookup": {"from": "cars", "localField": "car_id", "foreignField": "_id", "as": "car"}},
            {"$unwind": "$car"},
            {"$group": {"_id": "$car.brand", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]))
        self.show_report("Продажи по маркам", ["Марка", "Количество"], [(r['_id'], r['count']) for r in result])

    def report_revenue_by_payment(self):
        result = list(self.sales.aggregate([
            {"$lookup": {"from": "cars", "localField": "car_id", "foreignField": "_id", "as": "car"}},
            {"$unwind": "$car"},
            {"$group": {"_id": "$payment_type", "total": {"$sum": "$car.price"}}},
            {"$sort": {"total": -1}}
        ]))
        self.show_report("Выручка по типу оплаты", ["Тип оплаты", "Сумма"], [(r['_id'], r['total']) for r in result])

    def report_avg_price_by_color(self):
        result = list(self.sales.aggregate([
            {"$lookup": {"from": "cars", "localField": "car_id", "foreignField": "_id", "as": "car"}},
            {"$unwind": "$car"},
            {"$group": {"_id": "$car.color", "avg_price": {"$avg": "$car.price"}}},
            {"$sort": {"avg_price": -1}}
        ]))
        self.show_report("Средняя цена по цвету", ["Цвет", "Средняя цена"], [(r['_id'], round(r['avg_price'], 2)) for r in result])

    # --- ОТЧЁТЫ (простые запросы) ---
    def report_clients_by_name(self):
        name = simpledialog.askstring("Поиск клиента", "Введите часть ФИО:")
        if not name:
            return
        result = self.clients.find({"full_name": {"$regex": name, "$options": "i"}})
        self.show_report("Клиенты по ФИО", ["ФИО", "Паспорт", "Адрес", "Телефон"],
            [(c['full_name'], c['passport'], c['address'], c['phone']) for c in result])

    def report_sales_by_month(self):
        month = simpledialog.askstring("Месяц", "Введите месяц в формате YYYY-MM:")
        if not month:
            return
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
            # Получаем конец месяца
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            result = self.sales.find({
                "date": {"$gte": start, "$lt": next_month}
            })
            rows = []
            for s in result:
                car = self.cars.find_one({'_id': s['car_id']})
                client = self.clients.find_one({'_id': s['client_id']})
                rows.append((
                    car['brand'] + " " + car['model'] if car else "",
                    client['full_name'] if client else "",
                    s['date'].strftime("%Y-%m-%d") if s.get('date') else "",
                    s.get('payment_type', "")
                ))
            self.show_report("Продажи за месяц", ["Автомобиль", "Клиент", "Дата", "Тип оплаты"], rows)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Некорректный формат месяца (пример: 2025-06)")

    def report_cars_by_color(self):
        color = simpledialog.askstring("Цвет", "Введите цвет автомобиля:")
        if not color:
            return
        result = self.cars.find({"color": {"$regex": color, "$options": "i"}})
        self.show_report("Автомобили по цвету", ["Марка", "Модель", "Цвет", "Цена"],
            [(c['brand'], c['model'], c['color'], c['price']) for c in result])

    # --- ВКЛАДКИ ---
    def setup_cars_tab(self):
        self.cars_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cars_frame, text="Автомобили")
        columns = ('brand', 'model', 'color', 'price', 'in_stock')
        self.cars_tree = ttk.Treeview(self.cars_frame, columns=columns, show='headings')
        for col in columns:
            self.cars_tree.heading(col, text=col.capitalize())
            self.cars_tree.column(col, width=120)
        self.cars_tree.pack(fill='both', expand=True, padx=10, pady=10)

    def setup_clients_tab(self):
        self.clients_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.clients_frame, text="Клиенты")
        columns = ('full_name', 'passport', 'address', 'phone')
        self.clients_tree = ttk.Treeview(self.clients_frame, columns=columns, show='headings')
        for col in columns:
            self.clients_tree.heading(col, text=col.replace('_', ' ').capitalize())
            self.clients_tree.column(col, width=150)
        self.clients_tree.pack(fill='both', expand=True, padx=10, pady=10)

    def setup_sales_tab(self):
        self.sales_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sales_frame, text="Продажи")
        columns = ('car', 'client', 'date', 'delivery', 'payment_type')
        self.sales_tree = ttk.Treeview(self.sales_frame, columns=columns, show='headings')
        for col in columns:
            self.sales_tree.heading(col, text=col.capitalize())
            self.sales_tree.column(col, width=140)
        self.sales_tree.pack(fill='both', expand=True, padx=10, pady=10)

    def setup_buttons(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        self.add_btn = tk.Button(btn_frame, text="Добавить", width=12, command=self.add_item)
        self.edit_btn = tk.Button(btn_frame, text="Изменить", width=12, command=self.edit_item)
        self.delete_btn = tk.Button(btn_frame, text="Удалить", width=12, command=self.delete_item)
        self.refresh_btn = tk.Button(btn_frame, text="Обновить", width=12, command=self.refresh_all)

        self.add_btn.pack(side=tk.LEFT, padx=5)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        if self.user_role == "read":
            self.add_btn.config(state="disabled")
            self.edit_btn.config(state="disabled")
            self.delete_btn.config(state="disabled")
        elif self.user_role == "edit":
            self.delete_btn.config(state="disabled")

    def refresh_all(self):
        self.refresh_cars()
        self.refresh_clients()
        self.refresh_sales()

    def refresh_cars(self):
        for item in self.cars_tree.get_children():
            self.cars_tree.delete(item)
        for car in self.cars.find():
            self.cars_tree.insert('', 'end', iid=str(car['_id']), values=(
                car.get('brand', ''),
                car.get('model', ''),
                car.get('color', ''),
                car.get('price', ''),
                'Да' if car.get('in_stock', False) else 'Нет'
            ))

    def refresh_clients(self):
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
        for client in self.clients.find():
            self.clients_tree.insert('', 'end', iid=str(client['_id']), values=(
                client.get('full_name', ''),
                client.get('passport', ''),
                client.get('address', ''),
                client.get('phone', '')
            ))

    def refresh_sales(self):
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)
        for sale in self.sales.find():
            car = self.cars.find_one({'_id': sale['car_id']})
            client = self.clients.find_one({'_id': sale['client_id']})
            car_str = f"{car.get('brand', '')} {car.get('model', '')}" if car else "Не найден"
            client_str = client.get('full_name', '') if client else "Не найден"
            date_str = sale.get('date').strftime("%Y-%m-%d") if sale.get('date') else ""
            self.sales_tree.insert('', 'end', iid=str(sale['_id']), values=(
                car_str,
                client_str,
                date_str,
                'Да' if sale.get('delivery', False) else 'Нет',
                sale.get('payment_type', '')
            ))

    def add_item(self):
        tab = self.notebook.index(self.notebook.select())
        if tab == 0:
            self.add_car()
        elif tab == 1:
            self.add_client()
        elif tab == 2:
            self.add_sale()

    def edit_item(self):
        tab = self.notebook.index(self.notebook.select())
        if tab == 0:
            self.edit_car()
        elif tab == 1:
            self.edit_client()
        elif tab == 2:
            self.edit_sale()

    def delete_item(self):
        tab = self.notebook.index(self.notebook.select())
        if tab == 0:
            self.delete_car()
        elif tab == 1:
            self.delete_client()
        elif tab == 2:
            self.delete_sale()

    # --- CRUD для автомобилей ---
    def add_car(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить автомобиль")
        tk.Label(dialog, text="Марка:").grid(row=0, column=0, padx=5, pady=5)
        brand_entry = tk.Entry(dialog)
        brand_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Модель:").grid(row=1, column=0, padx=5, pady=5)
        model_entry = tk.Entry(dialog)
        model_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Цвет:").grid(row=2, column=0, padx=5, pady=5)
        color_entry = tk.Entry(dialog)
        color_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Цена:").grid(row=3, column=0, padx=5, pady=5)
        price_entry = tk.Entry(dialog)
        price_entry.grid(row=3, column=1, padx=5, pady=5)
        tk.Label(dialog, text="В наличии:").grid(row=4, column=0, padx=5, pady=5)
        in_stock_var = tk.BooleanVar(value=True)
        in_stock_check = tk.Checkbutton(dialog, variable=in_stock_var)
        in_stock_check.grid(row=4, column=1, padx=5, pady=5)
        def save():
            try:
                price = float(price_entry.get())
                self.cars.insert_one({
                    'brand': brand_entry.get(),
                    'model': model_entry.get(),
                    'color': color_entry.get(),
                    'price': price,
                    'in_stock': in_stock_var.get()
                })
                self.refresh_cars()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при добавлении: {e}")
        tk.Button(dialog, text="Сохранить", command=save).grid(row=5, columnspan=2, pady=10)

    def edit_car(self):
        selected = self.cars_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите автомобиль для редактирования.")
            return
        car_id = ObjectId(selected[0])
        car = self.cars.find_one({'_id': car_id})
        if not car:
            messagebox.showerror("Ошибка", "Автомобиль не найден.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Изменить автомобиль")

        tk.Label(dialog, text="Марка:").grid(row=0, column=0, padx=5, pady=5)
        brand_entry = tk.Entry(dialog)
        brand_entry.insert(0, car.get('brand', ''))
        brand_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Модель:").grid(row=1, column=0, padx=5, pady=5)
        model_entry = tk.Entry(dialog)
        model_entry.insert(0, car.get('model', ''))
        model_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Цвет:").grid(row=2, column=0, padx=5, pady=5)
        color_entry = tk.Entry(dialog)
        color_entry.insert(0, car.get('color', ''))
        color_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Цена:").grid(row=3, column=0, padx=5, pady=5)
        price_entry = tk.Entry(dialog)
        price_entry.insert(0, str(car.get('price', '')))
        price_entry.grid(row=3, column=1, padx=5, pady=5)
        tk.Label(dialog, text="В наличии:").grid(row=4, column=0, padx=5, pady=5)
        in_stock_var = tk.BooleanVar(value=car.get('in_stock', False))
        in_stock_check = tk.Checkbutton(dialog, variable=in_stock_var)
        in_stock_check.grid(row=4, column=1, padx=5, pady=5)
        def save():
            try:
                price = float(price_entry.get())
                self.cars.update_one({'_id': car_id}, {'$set': {
                    'brand': brand_entry.get(),
                    'model': model_entry.get(),
                    'color': color_entry.get(),
                    'price': price,
                    'in_stock': in_stock_var.get()
                }})
                self.refresh_cars()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при изменении: {e}")
        tk.Button(dialog, text="Сохранить", command=save).grid(row=5, columnspan=2, pady=10)

    def delete_car(self):
        selected = self.cars_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите автомобиль для удаления.")
            return
        car_id = ObjectId(selected[0])
        if messagebox.askyesno("Подтверждение", "Удалить выбранный автомобиль?"):
            self.cars.delete_one({'_id': car_id})
            self.refresh_cars()

    # --- CRUD для клиентов ---
    def add_client(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить клиента")
        tk.Label(dialog, text="ФИО:").grid(row=0, column=0, padx=5, pady=5)
        name_entry = tk.Entry(dialog)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Паспорт:").grid(row=1, column=0, padx=5, pady=5)
        passport_entry = tk.Entry(dialog)
        passport_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Адрес:").grid(row=2, column=0, padx=5, pady=5)
        address_entry = tk.Entry(dialog)
        address_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Телефон:").grid(row=3, column=0, padx=5, pady=5)
        phone_entry = tk.Entry(dialog)
        phone_entry.grid(row=3, column=1, padx=5, pady=5)
        def save():
            try:
                self.clients.insert_one({
                    'full_name': name_entry.get(),
                    'passport': passport_entry.get(),
                    'address': address_entry.get(),
                    'phone': phone_entry.get()
                })
                self.refresh_clients()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при добавлении клиента: {e}")
        tk.Button(dialog, text="Сохранить", command=save).grid(row=4, columnspan=2, pady=10)

    def edit_client(self):
        selected = self.clients_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите клиента для редактирования.")
            return
        client_id = ObjectId(selected[0])
        client = self.clients.find_one({'_id': client_id})
        if not client:
            messagebox.showerror("Ошибка", "Клиент не найден.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Изменить клиента")
        tk.Label(dialog, text="ФИО:").grid(row=0, column=0, padx=5, pady=5)
        name_entry = tk.Entry(dialog)
        name_entry.insert(0, client.get('full_name', ''))
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Паспорт:").grid(row=1, column=0, padx=5, pady=5)
        passport_entry = tk.Entry(dialog)
        passport_entry.insert(0, client.get('passport', ''))
        passport_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Адрес:").grid(row=2, column=0, padx=5, pady=5)
        address_entry = tk.Entry(dialog)
        address_entry.insert(0, client.get('address', ''))
        address_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Телефон:").grid(row=3, column=0, padx=5, pady=5)
        phone_entry = tk.Entry(dialog)
        phone_entry.insert(0, client.get('phone', ''))
        phone_entry.grid(row=3, column=1, padx=5, pady=5)
        def save():
            try:
                self.clients.update_one({'_id': client_id}, {'$set': {
                    'full_name': name_entry.get(),
                    'passport': passport_entry.get(),
                    'address': address_entry.get(),
                    'phone': phone_entry.get()
                }})
                self.refresh_clients()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при изменении клиента: {e}")
        tk.Button(dialog, text="Сохранить", command=save).grid(row=4, columnspan=2, pady=10)

    def delete_client(self):
        selected = self.clients_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите клиента для удаления.")
            return
        client_id = ObjectId(selected[0])
        if messagebox.askyesno("Подтверждение", "Удалить выбранного клиента?"):
            self.clients.delete_one({'_id': client_id})
            self.refresh_clients()

    # --- CRUD для продаж ---
    def add_sale(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить продажу")
        tk.Label(dialog, text="Автомобиль:").grid(row=0, column=0, padx=5, pady=5)
        cars_list = list(self.cars.find())
        car_var = tk.StringVar()
        car_combo = ttk.Combobox(dialog, textvariable=car_var, state='readonly')
        car_combo['values'] = [f"{c['brand']} {c['model']}" for c in cars_list]
        car_combo.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Клиент:").grid(row=1, column=0, padx=5, pady=5)
        clients_list = list(self.clients.find())
        client_var = tk.StringVar()
        client_combo = ttk.Combobox(dialog, textvariable=client_var, state='readonly')
        client_combo['values'] = [c['full_name'] for c in clients_list]
        client_combo.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Дата (ГГГГ-ММ-ДД):").grid(row=2, column=0, padx=5, pady=5)
        date_entry = tk.Entry(dialog)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Доставка:").grid(row=3, column=0, padx=5, pady=5)
        delivery_var = tk.BooleanVar(value=False)
        delivery_check = tk.Checkbutton(dialog, variable=delivery_var)
        delivery_check.grid(row=3, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Тип оплаты:").grid(row=4, column=0, padx=5, pady=5)
        payment_var = tk.StringVar()
        payment_combo = ttk.Combobox(dialog, textvariable=payment_var, state='readonly')
        payment_combo['values'] = ["cash", "credit", "transfer"]
        payment_combo.current(0)
        payment_combo.grid(row=4, column=1, padx=5, pady=5)
        def save():
            try:
                car_idx = car_combo.current()
                client_idx = client_combo.current()
                if car_idx == -1 or client_idx == -1:
                    messagebox.showwarning("Ошибка", "Выберите автомобиль и клиента.")
                    return
                date_obj = datetime.strptime(date_entry.get(), "%Y-%m-%d")
                self.sales.insert_one({
                    'car_id': cars_list[car_idx]['_id'],
                    'client_id': clients_list[client_idx]['_id'],
                    'date': date_obj,
                    'delivery': delivery_var.get(),
                    'payment_type': payment_var.get()
                })
                self.refresh_sales()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при добавлении продажи: {e}")
        tk.Button(dialog, text="Сохранить", command=save).grid(row=5, columnspan=2, pady=10)

    def edit_sale(self):
        selected = self.sales_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите продажу для редактирования.")
            return
        sale_id = ObjectId(selected[0])
        sale = self.sales.find_one({'_id': sale_id})
        if not sale:
            messagebox.showerror("Ошибка", "Продажа не найдена.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Изменить продажу")
        cars_list = list(self.cars.find())
        clients_list = list(self.clients.find())
        tk.Label(dialog, text="Автомобиль:").grid(row=0, column=0, padx=5, pady=5)
        car_var = tk.StringVar()
        car_combo = ttk.Combobox(dialog, textvariable=car_var, state='readonly')
        car_combo['values'] = [f"{c['brand']} {c['model']}" for c in cars_list]
        car_idx = next((i for i, c in enumerate(cars_list) if c['_id'] == sale['car_id']), 0)
        car_combo.current(car_idx)
        car_combo.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Клиент:").grid(row=1, column=0, padx=5, pady=5)
        client_var = tk.StringVar()
        client_combo = ttk.Combobox(dialog, textvariable=client_var, state='readonly')
        client_combo['values'] = [c['full_name'] for c in clients_list]
        client_idx = next((i for i, c in enumerate(clients_list) if c['_id'] == sale['client_id']), 0)
        client_combo.current(client_idx)
        client_combo.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Дата (ГГГГ-ММ-ДД):").grid(row=2, column=0, padx=5, pady=5)
        date_entry = tk.Entry(dialog)
        date_entry.insert(0, sale['date'].strftime("%Y-%m-%d") if sale.get('date') else "")
        date_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Доставка:").grid(row=3, column=0, padx=5, pady=5)
        delivery_var = tk.BooleanVar(value=sale.get('delivery', False))
        delivery_check = tk.Checkbutton(dialog, variable=delivery_var)
        delivery_check.grid(row=3, column=1, padx=5, pady=5)
        tk.Label(dialog, text="Тип оплаты:").grid(row=4, column=0, padx=5, pady=5)
        payment_var = tk.StringVar(value=sale.get('payment_type', 'cash'))
        payment_combo = ttk.Combobox(dialog, textvariable=payment_var, state='readonly')
        payment_combo['values'] = ["cash", "credit", "transfer"]
        payment_combo.grid(row=4, column=1, padx=5, pady=5)
        def save():
            try:
                car_idx = car_combo.current()
                client_idx = client_combo.current()
                if car_idx == -1 or client_idx == -1:
                    messagebox.showwarning("Ошибка", "Выберите автомобиль и клиента.")
                    return
                date_obj = datetime.strptime(date_entry.get(), "%Y-%m-%d")
                self.sales.update_one({'_id': sale_id}, {'$set': {
                    'car_id': cars_list[car_idx]['_id'],
                    'client_id': clients_list[client_idx]['_id'],
                    'date': date_obj,
                    'delivery': delivery_var.get(),
                    'payment_type': payment_var.get()
                }})
                self.refresh_sales()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при изменении продажи: {e}")
        tk.Button(dialog, text="Сохранить", command=save).grid(row=5, columnspan=2, pady=10)

    def delete_sale(self):
        selected = self.sales_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите продажу для удаления.")
            return
        sale_id = ObjectId(selected[0])
        if messagebox.askyesno("Подтверждение", "Удалить выбранную продажу?"):
            self.sales.delete_one({'_id': sale_id})
            self.refresh_sales()

def run_app():
    root = tk.Tk()
    login = LoginDialog(root, title="Вход")
    username = getattr(login, "username", None)
    password = getattr(login, "password", None)
    if username in USERS and USERS[username]["password"] == password:
        user_role = USERS[username]["role"]
        app = CarDealerApp(root, user_role, run_app)
        root.mainloop()
    else:
        if username is not None:
            messagebox.showerror("Ошибка входа", "Неверный логин или пароль!")

if __name__ == '__main__':
    run_app()
