from flask import Flask, render_template, redirect, url_for, flash, request, abort
from models import db, Book, Tag, User, Review, Cart, Rental
from forms import RegistrationForm, LoginForm, UploadBookForm, ReviewForm, RentalForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import base64, os

app = Flask(__name__, static_url_path='', static_folder='static')

app.config['SECRET_KEY'] = 'your_secret_key'
# เปลี่ยนการเชื่อมต่อฐานข้อมูลเป็น MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://bookie:72nh3khh@bookie.mysql.pythonanywhere-services.com/bookie$web'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)  # เปิดใช้งาน Migrate

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.template_filter('b64encode')
def b64encode_filter(data):
    """Filter to convert binary data to base64."""
    return base64.b64encode(data).decode('utf-8') if data else ''

@app.route('/')
def home():

    recommended_books = Book.query.filter_by(is_available=True).order_by(Book.rating.desc()).limit(5).all()
    new_release_books = Book.query.filter_by(is_available=True).order_by(Book.posted_at.desc()).limit(5).all()

    return render_template('home.html', recommended_books=recommended_books, new_release_books=new_release_books)

@app.route('/recommended', methods=['GET', 'POST'])
def recommended():
    search_query = request.args.get('search')  # รับค่าค้นหาจาก input

    if search_query:
        books = Book.query.filter(
            Book.is_available == True,
            Book.rating >= 4,
            (Book.title.ilike(f'%{search_query}%')) |
            (Book.author.ilike(f'%{search_query}%')) |
            (Book.tags.any(Tag.name.ilike(f'%{search_query}%')))
        ).all()
    else:
        books = Book.query.filter(
            Book.is_available == True,
            Book.rating >= 4
        ).all()

    return render_template('recommended.html', books=books)


@app.route('/new_releases', methods=['GET', 'POST'])
def new_releases():
    search_query = request.args.get('search')  # รับค่าค้นหาจาก input
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)

    if search_query:
        books = Book.query.filter(
            Book.is_available == True,
            Book.posted_at >= thirty_days_ago,
            (Book.title.ilike(f'%{search_query}%')) |
            (Book.author.ilike(f'%{search_query}%')) |
            (Book.tags.any(Tag.name.ilike(f'%{search_query}%')))
        ).all()
    else:
        books = Book.query.filter(
            Book.is_available == True,
            Book.posted_at >= thirty_days_ago
        ).all()

    return render_template('new_releases.html', books=books)


@app.route('/library', methods=['GET', 'POST'])
def library():
    search_query = request.args.get('search')  # รับค่าจาก input search
    if search_query:
        books = Book.query.filter(
            (Book.is_available == True),  # เงื่อนไขแสดงเฉพาะหนังสือที่ is_available=True
            (Book.title.ilike(f'%{search_query}%')) |  # ค้นหาด้วยชื่อหนังสือ
            (Book.author.ilike(f'%{search_query}%')) |  # ค้นหาด้วยชื่อผู้เขียน
            (Book.tags.any(Tag.name.ilike(f'%{search_query}%')))  # ค้นหาด้วย tag
        ).all()
    else:
        books = Book.query.filter_by(is_available=True).all()  # ถ้าไม่มีการค้นหาให้แสดงหนังสือที่ is_available=True ทั้งหมด

    return render_template('library.html', books=books)



@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('home'))  # รีไดเรกต์ไปหน้าหลัก
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')  # แสดงข้อความแสดงข้อผิดพลาด
    return render_template('login.html', form=form)

@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    user_cart = Cart.query.filter_by(user_id=current_user.id).all()  # ดึงข้อมูลตะกร้าของผู้ใช้
    form = RentalForm()

    # กำหนดค่าให้ SelectField
    form.book_id.choices = [(item.book.id, item.book.title) for item in user_cart]

    if form.validate_on_submit():
        book_id = form.book_id.data
        rental_days = form.rental_days.data
        rental = Rental(book_id=book_id, user_id=current_user.id, rental_days=rental_days)
        db.session.add(rental)
        db.session.commit()
        flash('Rental confirmed!', 'success')
        return redirect(url_for('my_shelf'))

    return render_template('cart.html', cart_items=user_cart, form=form)


@app.route('/remove_from_cart/<int:book_id>', methods=['POST'])
@login_required
def remove_from_cart(book_id):
    # ลบหนังสือออกจากตะกร้าของผู้ใช้
    cart_item = Cart.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash("Book removed from cart.")
    else:
        flash("Book not found in cart.")
    return redirect(url_for('cart'))


@app.route('/book/<int:book_id>', methods=['GET'])
def book_detail(book_id):
    book = Book.query.get(book_id)
    if book is None:
        flash("Book not found.")
        return redirect(url_for('library'))

    form = ReviewForm()

    return render_template('book_detail.html', book=book, form=form)

@app.route('/add_to_cart/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    book = Book.query.get(book_id)
    if book is None:
        flash("Book not found.")
        return redirect(url_for('library'))

    # เพิ่มหนังสือลงในตะกร้า
    current_user.add_to_cart(book)
    flash("Book added to cart.")
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/book/<int:book_id>/review', methods=['POST'])
@login_required
def submit_review(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            review_text=form.review_text.data,
            rating=form.rating.data,
            user_id=current_user.id,
            book_id=book.id
        )
        db.session.add(review)
        db.session.commit()

        book.update_rating()  # อัปเดตรคะแนนเฉลี่ยของหนังสือ

        flash('Your review has been submitted!', 'success')
        return redirect(url_for('book_detail', book_id=book.id))
    return render_template('book_detail.html', book=book, form=form)


@app.route('/my_shelf', methods=['GET'])
@login_required
def my_shelf():
    rented_books = Rental.query.filter_by(user_id=current_user.id, status = True).all()
    current_date = datetime.utcnow()

    for rental in rented_books:
        rental.end_date = rental.rented_on + timedelta(days=rental.rental_days)  # คำนวณวันที่สิ้นสุด
        rental.txt_available = bool(rental.book.txt_path)
    return render_template('my_shelf.html', rented_books=rented_books, current_date=current_date)

@app.route('/clear_expired', methods=['POST'])
@login_required
def clear_expired():
    # ค้นหาการเช่าที่หมดอายุแล้วในชั้นหนังสือของผู้ใช้
    expired_rentals = Rental.query.filter(
        Rental.user_id == current_user.id
    ).all()

    # ลบการเช่าที่หมดอายุแล้ว
    for rental in expired_rentals:
        if rental.rented_on + timedelta(days=rental.rental_days) < datetime.utcnow():
            rental.status = False

    db.session.commit()

    flash('Expired rentals have been cleared from your shelf.', 'success')
    return redirect(url_for('my_shelf'))

@app.route('/view_txt/<filename>')
@login_required
def view_txt(filename):
    # ตรวจสอบ referrer
    if request.referrer is None or 'my_shelf' not in request.referrer:
        abort(403)  # ห้ามเข้าถึงถ้าไม่มาจาก my_shelf

    # ตรวจสอบเส้นทางไฟล์
    txt_path = os.path.join('uploads', 'books', filename)

    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        flash('File not found.', 'danger')
        return redirect(url_for('my_shelf'))

    return render_template('view_txt.html', content=content)


@app.route('/my_reviews')
@login_required
def my_reviews():
    reviews = Review.query.filter_by(user_id=current_user.id).all()
    return render_template('my_reviews.html', reviews=reviews)

@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    review = Review.query.get(review_id)
    if review:
        book = review.book  # รับหนังสือที่เกี่ยวข้อง
        db.session.delete(review)  # ลบรีวิว
        db.session.commit()  # บันทึกการเปลี่ยนแปลง
        book.update_rating()  # อัปเดตเรตติ้งของหนังสือ
        flash('Review deleted successfully!', 'success')
    else:
        flash('Review not found!', 'danger')
    return redirect(url_for('my_reviews'))  # เปลี่ยนไปยังหน้าที่ต้องการ


@app.route('/my_own_books')
@login_required
def my_own_books():
    # ดึงหนังสือที่อัปโหลดโดยผู้ใช้ปัจจุบันและยังเปิดให้เช่าอยู่
    books = Book.query.filter_by(owner_id=current_user.id, is_available=True).all()
    # books = Book.query.filter_by(owner_id=current_user.id, is_available=True).all()
    return render_template('my_own_books.html', books=books)

@app.route('/book/<int:book_id>/delete', methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.owner_id != current_user.id:
        flash("You are not authorized to delete this book.", "danger")
        return redirect(url_for('my_own_books'))

    # แทนที่จะลบหนังสือออกจากฐานข้อมูล เราจะทำให้หนังสือไม่พร้อมให้เช่า
    book.is_available = False

    # ค้นหาและลบหนังสือออกจากตะกร้าของผู้ใช้ที่มีอยู่
    Cart.query.filter_by(book_id=book_id).delete()

    db.session.commit()
    flash("The book has been deleted successfully!", "success")

    return redirect(url_for('my_own_books'))


@app.route('/upload_book', methods=['GET', 'POST'])
@login_required
def upload_book():
    form = UploadBookForm()

    if form.validate_on_submit():
        # สร้างโฟลเดอร์ถ้ายังไม่มี
        txt_folder = os.path.join('uploads', 'books')

        if not os.path.exists(txt_folder):
            os.makedirs(txt_folder)

        # สร้างหนังสือใหม่
        new_book = Book(
            title=form.title.data,
            author=form.author.data,
            description=form.description.data,
            price_per_day=form.price_per_day.data,
            owner_id=current_user.id
        )

        # จัดการแท็ก
        tags = form.tags.data.split(',')
        for tag_name in tags:
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                new_book.tags.append(tag)

        # จัดการไฟล์
        if form.txt_file.data:
            filename = secure_filename(form.txt_file.data.filename)
            txt_path = os.path.join(txt_folder, filename)
            form.txt_file.data.save(txt_path)
            new_book.txt_path = txt_path


        # จัดการรูปปก
        if form.cover_image.data:
            cover_image = form.cover_image.data.read()
            new_book.cover_image = cover_image
            new_book.cover_image_mime_type = form.cover_image.data.mimetype

        # บันทึกหนังสือ
        db.session.add(new_book)
        db.session.commit()

        flash('Book uploaded successfully!', 'success')
        return redirect(url_for('my_own_books'))

    return render_template('upload_book.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
