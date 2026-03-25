// Переключаемся на базу данных
use car_dealer

// Очищаем коллекции, если они уже были
db.cars.drop()
db.clients.drop()
db.sales.drop()

// 1. Добавляем автомобили
const cars = [
  { brand: "Toyota", model: "Camry", color: "Белый", price: 2500000, in_stock: true },
  { brand: "BMW", model: "X5", color: "Черный", price: 4500000, in_stock: false },
  { brand: "Hyundai", model: "Solaris", color: "Синий", price: 1800000, in_stock: true },
  { brand: "Kia", model: "Rio", color: "Красный", price: 1700000, in_stock: true },
  { brand: "Lada", model: "Vesta", color: "Серый", price: 1200000, in_stock: false }
]
const car_ids = db.cars.insertMany(cars).insertedIds

// 2. Добавляем клиентов
const clients = [
  { full_name: "Иванов Иван Иванович", passport: "1234 567890", address: "Москва, ул. Ленина, д.1", phone: "+7 999 123-45-67" },
  { full_name: "Петрова Мария Сергеевна", passport: "4321 098765", address: "Санкт-Петербург, пр. Мира, д.2", phone: "+7 921 555-11-22" },
  { full_name: "Сидоров Алексей Петрович", passport: "5678 123456", address: "Казань, ул. Победы, д.3", phone: "+7 843 777-88-99" },
  { full_name: "Кузнецова Ольга Дмитриевна", passport: "8765 654321", address: "Екатеринбург, ул. Уральская, д.4", phone: "+7 343 333-44-55" },
  { full_name: "Васильев Павел Андреевич", passport: "3456 789012", address: "Новосибирск, ул. Лесная, д.5", phone: "+7 383 222-33-44" }
]
const client_ids = db.clients.insertMany(clients).insertedIds

// 3. Добавляем продажи (используем реальные ObjectId из cars и clients)
db.sales.insertMany([
  {
    car_id: car_ids[0],
    client_id: client_ids[0],
    date: ISODate("2025-06-10T10:00:00Z"),
    delivery: true,
    payment_type: "credit"
  },
  {
    car_id: car_ids[1],
    client_id: client_ids[1],
    date: ISODate("2025-06-12T14:30:00Z"),
    delivery: false,
    payment_type: "cash"
  },
  {
    car_id: car_ids[2],
    client_id: client_ids[2],
    date: ISODate("2025-06-15T09:00:00Z"),
    delivery: true,
    payment_type: "transfer"
  },
  {
    car_id: car_ids[3],
    client_id: client_ids[3],
    date: ISODate("2025-06-18T16:45:00Z"),
    delivery: false,
    payment_type: "credit"
  },
  {
    car_id: car_ids[4],
    client_id: client_ids[4],
    date: ISODate("2025-06-20T11:20:00Z"),
    delivery: true,
    payment_type: "cash"
  }
])

// 1. Пользователь только для чтения
db.createUser({
  user: "reader",
  pwd: "reader_pass",
  roles: [ { role: "read", db: "car_dealer" } ]
})

// 2. Пользователь с правами чтения и изменения
db.createUser({
  user: "editor",
  pwd: "editor_pass",
  roles: [ { role: "readWrite", db: "car_dealer" } ]
})

// 3. Пользователь с полным доступом (администратор)
db.createUser({
  user: "admin",
  pwd: "admin_pass",
  roles: [ { role: "dbOwner", db: "car_dealer" } ]
})

db.cars.createIndex({ brand: 1 })
db.cars.createIndex({ model: 1 })
db.cars.createIndex({ color: 1 })
db.cars.createIndex({ in_stock: 1 })
db.clients.createIndex({ full_name: 1 })
db.clients.createIndex({ passport: 1 }, { unique: true })
db.sales.createIndex({ date: 1 })
db.sales.createIndex({ payment_type: 1 })
db.sales.createIndex({ car_id: 1 })
db.sales.createIndex({ client_id: 1 })
// db.cars.find().pretty()
// db.clients.find().pretty()
// db.sales.find().pretty()
