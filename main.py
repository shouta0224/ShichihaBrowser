import sys
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QWidget, QPushButton, QTabWidget, QToolButton,
                             QMenu, QMessageBox, QProgressBar)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineSettings
from PyQt5.QtCore import QUrl, Qt, QTimer, QObject, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor

class AdBlocker(QWebEngineUrlRequestInterceptor):
    def __init__(self, blocked_urls):
        super().__init__()
        self.blocked_urls = blocked_urls
    
    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        for blocked in self.blocked_urls:
            if blocked in url:
                info.block(True)
                break

class OptimizedBrowserTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.layout = QVBoxLayout(self)
        self.setup_ui()
        self.setup_optimizations()
    
    def setup_ui(self):
        # ナビゲーションバー
        self.nav_bar = QHBoxLayout()
        self.nav_bar.setContentsMargins(5, 5, 5, 5)
        
        # ナビゲーションボタン
        self.back_button = QPushButton("←")
        self.back_button.setFixedWidth(30)
        self.back_button.clicked.connect(self.go_back)
        self.nav_bar.addWidget(self.back_button)
        
        self.forward_button = QPushButton("→")
        self.forward_button.setFixedWidth(30)
        self.forward_button.clicked.connect(self.go_forward)
        self.nav_bar.addWidget(self.forward_button)
        
        self.reload_button = QPushButton("↻")
        self.reload_button.setFixedWidth(30)
        self.reload_button.clicked.connect(self.reload_page)
        self.nav_bar.addWidget(self.reload_button)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setStyleSheet("QProgressBar { background: transparent; }")
        
        # URLバー
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("URLを入力...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.nav_bar.addWidget(self.url_bar, stretch=1)
        
        # ブックマークボタン
        self.bookmark_button = QPushButton("★")
        self.bookmark_button.setFixedWidth(30)
        self.bookmark_button.clicked.connect(self.safe_add_to_bookmarks)
        self.nav_bar.addWidget(self.bookmark_button)
        
        self.layout.addLayout(self.nav_bar)
        self.layout.addWidget(self.progress_bar)
        
        # Webビュー
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl("about:blank"))
        self.web_view.urlChanged.connect(self.update_url)
        self.web_view.titleChanged.connect(self.update_title)
        self.web_view.loadProgress.connect(self.update_progress)
        self.web_view.loadStarted.connect(self.page_load_started)
        self.web_view.loadFinished.connect(self.page_load_finished)
        self.layout.addWidget(self.web_view, stretch=1)

    def safe_add_to_bookmarks(self):
        try:
            self.add_to_bookmarks()
        except Exception as e:
            print(f"ブックマーク追加エラー: {e}")
            QMessageBox.critical(self, "エラー", "ブックマークの追加に失敗しました")
    
    def setup_optimizations(self):
        # レンダリング設定
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)
        settings.setAttribute(QWebEngineSettings.AutoLoadIconsForPage, False)
        settings.setAttribute(QWebEngineSettings.XSSAuditingEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        
        # キャッシュとプロファイル設定
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        profile.setCachePath("web_cache")
        profile.setPersistentStoragePath("web_storage")
        
        # アドブロッカー
        blocked_urls = [
            "*://*.doubleclick.net/*",
            "*://*.googleadservices.com/*",
            "*://*.googlesyndication.com/*",
            "*://*.adservice.google.com/*",
            "*://*.adbrite.com/*",
            "*://*.exponential.com/*",
            "*://*.quantserve.com/*",
            "*://*.scorecardresearch.com/*"
        ]
        profile.setUrlRequestInterceptor(AdBlocker(blocked_urls))

        self.web_view.page().runJavaScript("""
            // 簡易アドブロッカー
            const blockedDomains = [
                'doubleclick.net',
                'googleadservices.com',
                'googlesyndication.com',
                'adservice.google.com'
            ];
            
            document.addEventListener('DOMNodeInserted', function(e) {
                blockedDomains.forEach(domain => {
                    if (e.target.src && e.target.src.includes(domain)) {
                        e.target.remove();
                    }
                    if (e.target.href && e.target.href.includes(domain)) {
                        e.target.remove();
                    }
                });
            });
        """)
        
        # メモリ管理
        self.web_view.setAttribute(Qt.WA_DeleteOnClose, True)
    
    def navigate_to_url(self):
        url = self.url_bar.text().strip()
        if not url:
            return
            
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_bar.setText(url)
            
        # 読み込みタイムアウト設定
        if hasattr(self, 'load_timer'):
            self.load_timer.stop()
            
        self.load_timer = QTimer(self)
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.handle_load_timeout)
        self.load_timer.start(15000)  # 15秒タイムアウト
        
        self.web_view.setUrl(QUrl(url))
    
    def handle_load_timeout(self):
        if self.progress_bar.value() < 100:
            self.web_view.stop()
            QMessageBox.warning(self, "読み込み遅延", 
                              "ページの読み込みに時間がかかっています。\nネットワーク接続を確認するか、後でもう一度試してください。")
    
    def update_progress(self, progress):
        self.progress_bar.setValue(progress)
    
    def page_load_started(self):
        self.progress_bar.setVisible(True)
    
    def page_load_finished(self, ok):
        self.progress_bar.setVisible(False)
        if hasattr(self, 'load_timer'):
            self.load_timer.stop()
        
        if not ok:
            self.progress_bar.setStyleSheet("QProgressBar { background: transparent; border: 1px solid red; }")
            QTimer.singleShot(3000, lambda: self.progress_bar.setStyleSheet("QProgressBar { background: transparent; }"))
    
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
        try:
            url = self.web_view.url().toString()
            title = self.web_view.title()
            
            if not title or title == "about:blank":
                title = url
                
            if self.parent:
                QTimer.singleShot(0, lambda: self.parent.add_bookmark_safely(title, url))
        except Exception as e:
            print(f"ブックマーク追加エラー: {e}")
            QMessageBox.critical(self, "エラー", "ブックマーク追加中に問題が発生しました")

class TabBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optimized Browser")
        self.setGeometry(100, 100, 1200, 800)
        self.bookmarks = {}
        self.load_bookmarks()
        self.setup_ui()

    def safe_add_bookmark(self, title, url):
        try:
            if url not in self.bookmarks.values():
                # 重複タイトル処理
                if title in self.bookmarks:
                    title = f"{title} ({len([k for k in self.bookmarks.keys() if k.startswith(title)]) + 1})"
                
                self.bookmarks[title] = url
                self.save_bookmarks()
                self.setup_bookmark_bar()
                QMessageBox.information(self, "成功", f"ブックマークに追加しました: {title}")
        except Exception as e:
            print(f"ブックマーク保存エラー: {e}")
            QMessageBox.critical(self, "エラー", "ブックマークの保存に失敗しました")
    
    def setup_ui(self):
        # メインウィジェット
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_widget.setLayout(self.main_layout)
        
        # ブックマークバー
        self.bookmark_bar = QHBoxLayout()
        self.bookmark_bar.setContentsMargins(5, 2, 5, 2)
        self.bookmark_bar.setSpacing(5)
        self.setup_bookmark_bar()
        self.main_layout.addLayout(self.bookmark_bar)
        
        # タブウィジェット
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.cleanup_tabs)
        self.main_layout.addWidget(self.tabs)
        
        # 新しいタブボタン
        self.new_tab_button = QPushButton("+")
        self.new_tab_button.setFixedWidth(30)
        self.new_tab_button.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.new_tab_button)
        
        # 初期タブ
        self.add_new_tab("https://www.google.com")
    
    def setup_bookmark_bar(self):
        # ブックマークバーをクリア
        for i in reversed(range(self.bookmark_bar.count())): 
            widget = self.bookmark_bar.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 管理ボタン
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
        
        # ブックマークボタン
        for title, url in self.bookmarks.items():
            btn = QPushButton(title)
            btn.setToolTip(url)
            btn.setMaximumWidth(150)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 2px;
                    border: none;
                    background: transparent;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                }
            """)
            btn.clicked.connect(lambda checked, u=url: self.open_bookmark(u))
            self.bookmark_bar.addWidget(btn)
        
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
            QTimer.singleShot(100, lambda: current_tab.safe_add_to_bookmarks())
    
    def open_bookmark(self, url):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.web_view.setUrl(QUrl(url))
    
    def manage_bookmarks(self):
        msg = QMessageBox()
        msg.setWindowTitle("ブックマーク管理")
        msg.setText(f"登録ブックマーク数: {len(self.bookmarks)}")
        
        bookmarks_text = "\n".join([f"・{title}: {url}" for title, url in self.bookmarks.items()])
        msg.setDetailedText(bookmarks_text)
        
        clear_btn = msg.addButton("全削除", QMessageBox.ActionRole)
        export_btn = msg.addButton("エクスポート", QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Close)
        
        ret = msg.exec_()
        
        if msg.clickedButton() == clear_btn:
            self.clear_all_bookmarks()
        elif msg.clickedButton() == export_btn:
            self.export_bookmarks()
    
    def clear_all_bookmarks(self):
        reply = QMessageBox.question(self, "確認", "すべてのブックマークを削除しますか？",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.bookmarks.clear()
            self.save_bookmarks()
            self.setup_bookmark_bar()
    
    def export_bookmarks(self):
        options = QFileDialog.Options()
        path, _ = QFileDialog.getSaveFileName(self, "ブックマークを保存", "", 
                                            "HTMLファイル (*.html);;すべてのファイル (*)", 
                                            options=options)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n")
                f.write("<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">\n")
                f.write("<TITLE>Bookmarks</TITLE>\n<H1>Bookmarks</H1>\n<DL><p>\n")
                for title, url in self.bookmarks.items():
                    f.write(f"    <DT><A HREF=\"{url}\">{title}</A>\n")
                f.write("</DL><p>\n")
            QMessageBox.information(self, "成功", "ブックマークをエクスポートしました")
    
    def load_bookmarks(self):
        try:
            with open('bookmarks.json', 'r', encoding='utf-8') as f:
                self.bookmarks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.bookmarks = {
                "Google": "https://www.google.com",
                "YouTube": "https://www.youtube.com",
                "GitHub": "https://github.com",
                "DuckDuckGo": "https://duckduckgo.com"
            }
            self.save_bookmarks()
    
    def save_bookmarks(self):
        with open('bookmarks.json', 'w', encoding='utf-8') as f:
            json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
    
    def add_new_tab(self, url=None):
        tab = OptimizedBrowserTab(self)
        index = self.tabs.addTab(tab, "新しいタブ")
        self.tabs.setCurrentIndex(index)
        
        if url:
            tab.web_view.setUrl(QUrl(url))
        
        tab.web_view.titleChanged.connect(
            lambda title, tab=tab: self.update_tab_title(tab, title))
    
    def close_tab(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            widget.deleteLater()
            self.tabs.removeTab(index)
    
    def cleanup_tabs(self):
        # 非アクティブなタブのリソースを解放
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget and i != self.tabs.currentIndex():
                widget.web_view.page().setVisible(False)
            elif widget:
                widget.web_view.page().setVisible(True)
    
    def update_tab_title(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index != -1:
            short_title = (title[:15] + '...') if len(title) > 18 else title
            self.tabs.setTabText(index, short_title)
            self.tabs.setTabToolTip(index, f"{title}\n{tab.web_view.url().toString()}")

    def add_bookmark_safely(self, title, url):
        try:
            if not url or url == "about:blank":
                return
                
            if url in self.bookmarks.values():
                QMessageBox.information(self, "情報", "このURLは既にブックマークに存在します")
                return
                
            if title in self.bookmarks:
                base_title = title
                counter = 1
                while f"{base_title} ({counter})" in self.bookmarks:
                    counter += 1
                title = f"{base_title} ({counter})"
                
            self.bookmarks[title] = url
            self.save_bookmarks()
            QTimer.singleShot(0, self.setup_bookmark_bar)
            
        except Exception as e:
            print(f"ブックマーク保存エラー: {e}")
            QMessageBox.critical(self, "エラー", "ブックマークの保存に失敗しました")
    
    def open_bookmark_safely(self, url):
        try:
            current_tab = self.tabs.currentWidget()
            if current_tab and url:
                current_tab.web_view.setUrl(QUrl(url))
        except Exception as e:
            print(f"ブックマークオープンエラー: {e}")
    
    def setup_bookmark_bar(self):
        try:
            while self.bookmark_bar.count() > 0:
                item = self.bookmark_bar.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
            manage_button = QToolButton()
            manage_button.setText("≡")
            manage_menu = QMenu()
            
            # ...（メニュー設定）...
            
            for title, url in self.bookmarks.items():
                btn = QPushButton(title)
                btn.setToolTip(url)
                btn.setMaximumWidth(150)
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 2px 5px;
                        border: none;
                        background: transparent;
                    }
                    QPushButton:hover {
                        background: #e0e0e0;
                    }
                """)
                btn.clicked.connect(
                    lambda checked, u=url: self.open_bookmark_safely(u))
                self.bookmark_bar.addWidget(btn)
                
            self.bookmark_bar.addStretch(1)
        except Exception as e:
            print(f"ブックマークバー更新エラー: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 高DPI対応
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    browser = TabBrowser()
    browser.show()
    
    # メモリリーク防止
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(1000)
    
    sys.exit(app.exec_())
