from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secret_key'

# SQLAlchemy 資料庫設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask-Login 設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 使用者資料庫模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # 判斷是否為管理員

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    publish_date = db.Column(db.String(100), nullable=True)
    is_borrowed = db.Column(db.Boolean, default=False)
    borrowed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    borrower = db.relationship('User', backref='borrowed_books', foreign_keys=[borrowed_by])

# 初始化資料庫
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except ValueError:
        return None

# 首頁 - 書籍清單
@app.route('/')
@login_required
def index():
    books = Book.query.all()
    return render_template('index.html', books=books)

# 註冊頁面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 確認密碼一致
        if password != confirm_password:
            flash('密碼和確認密碼不一致')
            return redirect(url_for('register'))

        # 檢查是否為管理員註冊
        is_admin = 'admin' in request.form  # 檢查表單是否包含 admin 鍵

        # 新建使用者
        new_user = User(username=username,  password_hash=generate_password_hash(password), is_admin=is_admin)  # 設置 is_admin

        db.session.add(new_user)
        db.session.commit()
        
        flash('註冊成功！')
        return redirect(url_for('login'))

    return render_template('register.html')

# 登入頁面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 查找使用者
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            # 登入成功
            login_user(user)
            # flash('登入成功！', 'success')
            return redirect(url_for('index'))
        else:
            # 登入失敗
            flash('使用者名稱或密碼錯誤，請重試。', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

# 登出
@app.route('/logout')
@login_required
def logout():
    logout_user()
    # 清除所有 flash 訊息
    session.pop('_flashes', None)
    flash('您已成功登出。', 'info')
    return redirect(url_for('login'))

# 借閱書籍
@app.route('/borrow/<int:book_id>')
@login_required
def borrow_book(book_id):
    book = Book.query.get(book_id)
    if book and not book.is_borrowed:
        book.is_borrowed = True
        book.borrowed_by = current_user.id  # 將借閱者設為當前使用者
        db.session.commit()
        flash('書籍已成功借閱！')
    else:
        flash('該書籍已被借閱或不存在。')
    return redirect(url_for('index'))

# 歸還書籍
@app.route('/return/<int:book_id>', methods=['POST'])
@login_required
def return_book(book_id):
    book = Book.query.get(book_id)
    if book and book.borrowed_by == current_user.id:
        book.is_borrowed = False
        book.borrowed_by = None
        db.session.commit()
        flash('書籍已成功歸還！')
    else:
        flash('無法歸還書籍。')
    return redirect(url_for('user_page'))

# 使用者頁面 - 顯示借閱書籍（需登入）
@app.route('/user')
@login_required
def user_page():
    # 查詢當前使用者借閱的書籍
    borrowed_books = Book.query.filter_by(borrowed_by=current_user.id).all()
    return render_template('user.html', borrowed_books=borrowed_books)
    

# 管理員功能：新增書籍
@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        flash('您沒有權限執行此操作！')
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        publish_date = request.form['publish_date']
        new_book = Book(title=title, author=author, publish_date=publish_date)
        db.session.add(new_book)
        db.session.commit()
        flash('書籍已成功新增！')
        return redirect(url_for('index'))
    return render_template('add_book.html')

# 管理員功能：刪除書籍
@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if not current_user.is_admin:
        flash('您沒有權限執行此操作！')
        return redirect(url_for('index'))
    book = Book.query.get(book_id)
    if book:
        db.session.delete(book)
        db.session.commit()
        flash('書籍已成功刪除！')
    else:
        flash('找不到該書籍。')
    return redirect(url_for('index'))

@app.route('/manage_users')
@login_required
def manage_users():
    # 確認使用者是否為管理員
    if not current_user.is_admin:
        flash('只有管理員可以訪問此頁面。')
        return redirect(url_for('index'))

    # 查詢所有使用者
    users = User.query.all()
    return render_template('manage_users.html', users=users)

# 刪除使用者功能
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    # 確認使用者是否為管理員
    if not current_user.is_admin:
        flash('只有管理員可以刪除使用者。')
        return redirect(url_for('index'))

    # 查找要刪除的使用者
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('使用者已刪除。')
    else:
        flash('找不到該使用者。')

    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    app.run(debug=True)
