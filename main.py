import sys
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QWidget, QPushButton, QTabWidget, QToolButton,
                             QMenu, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon

class BrowserTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.layout = QVBoxLayout(self)
        self.setup_ui()
    
    def setup_ui(self):
        # ナビゲーションバーのレイアウト
        self.nav_bar = QHBoxLayout()
        
        # ナビゲーションボタン
        self.back_button = QPushButton("←")
        self.back_button.clicked.connect(self.go_back)
        self.nav_bar.addWidget(self.back_button)
        
        self.forward_button = QPushButton("→")
        self.forward_button.clicked.connect(self.go_forward)
        self.nav_bar.addWidget(self.forward_button)
        
        self.reload_button = QPushButton("↻")
        self.reload_button.clicked.connect(self.reload_page)
        self.nav_bar.addWidget(self.reload_button)
        
        # URLバー
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.nav_bar.addWidget(self.url_bar, stretch=1)
        
        # ブックマーク追加ボタン
        self.bookmark_button = QPushButton("★")
        self.bookmark_button.clicked.connect(self.add_to_bookmarks)
        self.nav_bar.addWidget(self.bookmark_button)
        
        self.layout.addLayout(self.nav_bar)
        
        # Webビュー
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl("https://www.google.com"))
        self.url_bar.setText("https://www.google.com")
        self.web_view.urlChanged.connect(self.update_url)
        self.web_view.titleChanged.connect(self.update_title)
        self.layout.addWidget(self.web_view)
    
    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_bar.setText(url)
        self.web_view.setUrl(QUrl(url))
    
    def go_back(self):
        self.web_view.back()
    
    def go_forward(self):
        self.web_view.forward()
    
    def reload_page(self):
        self.web_view.reload()
    
    def update_url(self, url):
        self.url_bar.setText(url.toString())
    
    def update_title(self, title):
        if self.parent:
            self.parent.update_tab_title(self, title)
    
    def add_to_bookmarks(self):
        url = self.web_view.url().toString()
        title = self.web_view.title()
        if self.parent:
            self.parent.add_bookmark(title, url)

class TabBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Browser with Bookmarks")
        self.setGeometry(100, 100, 1200, 800)
        self.bookmarks = {}
        self.load_bookmarks()
        self.setup_ui()
    
    def setup_ui(self):
        # メインウィジェットとレイアウト
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        # ブックマークバー
        self.bookmark_bar = QHBoxLayout()
        self.bookmark_bar.setSpacing(5)
        self.setup_bookmark_bar()
        self.main_layout.addLayout(self.bookmark_bar)
        
        # タブウィジェット
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.main_layout.addWidget(self.tabs)
        
        # 新しいタブボタン
        self.new_tab_button = QPushButton("+")
        self.new_tab_button.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.new_tab_button)
        
        # 初期タブを追加
        self.add_new_tab()
    
    def setup_bookmark_bar(self):
        # ブックマークバーをクリア
        for i in reversed(range(self.bookmark_bar.count())): 
            self.bookmark_bar.itemAt(i).widget().setParent(None)
        
        # ブックマーク管理ボタン（左側に配置）
        manage_button = QToolButton()
        manage_button.setText("≡")
        manage_button.setPopupMode(QToolButton.InstantPopup)
        manage_menu = QMenu()
        
        edit_action = manage_menu.addAction("ブックマークを管理")
        edit_action.triggered.connect(self.manage_bookmarks)
        
        add_action = manage_menu.addAction("現在のページを追加")
        add_action.triggered.connect(self.add_current_to_bookmarks)
        
        manage_button.setMenu(manage_menu)
        self.bookmark_bar.addWidget(manage_button)
        
        # ブックマークをバーに追加（左から右へ）
        for title, url in self.bookmarks.items():
            btn = QPushButton(title)
            btn.setToolTip(url)
            btn.setMaximumWidth(150)
            btn.setStyleSheet("text-align: left;")
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn: self.show_bookmark_context_menu(pos, b))
            btn.clicked.connect(lambda checked, u=url: self.open_bookmark(u))
            self.bookmark_bar.addWidget(btn)
        
        # 右側にスペーサーを追加して左寄せにする
        self.bookmark_bar.addStretch(1)
    
    def show_bookmark_context_menu(self, pos, button):
        menu = QMenu()
        delete_action = menu.addAction("削除")
        delete_action.triggered.connect(lambda: self.remove_bookmark(button))
        menu.exec_(button.mapToGlobal(pos))
    
    def add_bookmark(self, title, url):
        if url not in self.bookmarks.values():
            self.bookmarks[title] = url
            self.save_bookmarks()
            self.setup_bookmark_bar()
    
    def remove_bookmark(self, button):
        title = button.text()
        if title in self.bookmarks:
            del self.bookmarks[title]
            self.save_bookmarks()
            self.setup_bookmark_bar()
    
    def add_current_to_bookmarks(self):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            url = current_tab.web_view.url().toString()
            title = current_tab.web_view.title()
            self.add_bookmark(title, url)
    
    def open_bookmark(self, url):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.web_view.setUrl(QUrl(url))
    
    def manage_bookmarks(self):
        msg = QMessageBox()
        msg.setWindowTitle("ブックマーク管理")
        msg.setText("現在のブックマーク:")
        
        bookmarks_text = "\n".join([f"{title}: {url}" for title, url in self.bookmarks.items()])
        msg.setInformativeText(bookmarks_text)
        
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def load_bookmarks(self):
        try:
            with open('bookmarks.json', 'r') as f:
                self.bookmarks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # デフォルトのブックマーク
            self.bookmarks = {
                "Google": "https://www.google.com",
                "YouTube": "https://www.youtube.com",
                "GitHub": "https://github.com"
            }
    
    def save_bookmarks(self):
        with open('bookmarks.json', 'w') as f:
            json.dump(self.bookmarks, f, indent=2)
    
    def add_new_tab(self):
        tab = BrowserTab(self)
        index = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(index)
        
        tab.web_view.titleChanged.connect(
            lambda title, tab=tab: self.update_tab_title(tab, title))
    
    def close_tab(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            widget.deleteLater()
            self.tabs.removeTab(index)
    
    def update_tab_title(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index != -1:
            short_title = (title[:15] + '...') if len(title) > 18 else title
            self.tabs.setTabText(index, short_title)
            self.tabs.setTabToolTip(index, title)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = TabBrowser()
    browser.show()
    sys.exit(app.exec_())
