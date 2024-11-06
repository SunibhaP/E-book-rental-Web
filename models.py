from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

    # Relationships
    reviews = db.relationship('Review', back_populates='user', lazy='dynamic')
    cart_items = db.relationship('Cart', back_populates='user', lazy='dynamic')
    books = db.relationship('Book', backref='owner', lazy=True)  # เชื่อมโยงผู้ใช้กับหนังสือที่ผู้ใช้เป็นเจ้าของ

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def add_to_cart(self, book):
        # ตรวจสอบว่าไม่ซ้ำในตะกร้า
        existing_item = Cart.query.filter_by(user_id=self.id, book_id=book.id).first()
        if not existing_item:
            new_item = Cart(user_id=self.id, book_id=book.id)
            db.session.add(new_item)
            db.session.commit()

book_tag = db.Table('book_tag',
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price_per_day = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float, nullable=True)
    txt_path = db.Column(db.String(256), nullable=True)
    cover_image = db.Column(db.LargeBinary, nullable=True)  # เก็บรูปหน้าปก
    cover_image_mime_type = db.Column(db.String(256), nullable=True)  # MIME type สำหรับรูปหน้าปก
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # เชื่อมโยงกับผู้ใช้เจ้าของหนังสือ
    posted_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_available = db.Column(db.Boolean, default=True)

    # Relationships
    reviews = db.relationship('Review', back_populates='book', cascade="all, delete-orphan")
    cart_items = db.relationship('Cart', back_populates='book', cascade="all, delete-orphan")
    tags = db.relationship('Tag', secondary='book_tag', back_populates='books')  # Many-to-many relationship with tags

    def update_rating(self):
        total_reviews = len(self.reviews)  # ใช้ len() แทน count()
        if total_reviews > 0:
            total_rating = sum([review.rating for review in self.reviews])
            self.rating = total_rating / total_reviews
        else:
            self.rating = None  # No rating if there are no reviews
        db.session.commit()

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    review_text = db.Column(db.Text, nullable=False)  # เปลี่ยนจาก text เป็น review_text
    rating = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='reviews')
    book = db.relationship('Book', back_populates='reviews')

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    books = db.relationship('Book', secondary=book_tag, back_populates='tags')

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='cart_items')
    book = db.relationship('Book', back_populates='cart_items')


class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rental_days = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)  # เพิ่มฟิลด์ total_price
    rented_on = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref='rentals')
    book = db.relationship('Book', backref='rentals')

    def __init__(self, book_id, user_id, rental_days):
        self.book_id = book_id
        self.user_id = user_id
        self.rental_days = rental_days
        self.total_price = self.calculate_total_price()

    def calculate_total_price(self):
        book = Book.query.get(self.book_id)  # ดึงข้อมูลหนังสือที่เช่า
        return book.price_per_day * self.rental_days if book else 0

