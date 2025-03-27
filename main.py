import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLineEdit, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class SimpleBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Browser")
        self.setGeometry(100, 100, 800, 600)
        
        # メインウィジェットとレイアウト
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # URL入力用のテキストボックス
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL and press Enter")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        layout.addWidget(self.url_bar)
        
        # Webページ表示用のビュー
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # 初期ページの読み込み（オプション）
        self.web_view.setUrl(QUrl("https://www.google.com"))
        self.url_bar.setText("https://www.google.com")

    def navigate_to_url(self):
        url = self.url_bar.text()
        # URLにhttp://またはhttps://が含まれていない場合は追加
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_bar.setText(url)
        self.web_view.setUrl(QUrl(url))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = SimpleBrowser()
    browser.show()
    sys.exit(app.exec_())
