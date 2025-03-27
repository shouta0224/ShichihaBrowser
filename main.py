import sys
import json
import re
import os
import importlib.util
from urllib.parse import urlparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QWidget, QPushButton, QTabWidget, QToolButton,
                             QMenu, QMessageBox, QProgressBar, QFileDialog, QStyleFactory)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineSettings
from PyQt5.QtCore import QUrl, Qt, QTimer, QObject, pyqtSlot, QStandardPaths
from PyQt5.QtGui import QIcon, QPalette, QColor
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

class PrivacyManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cookie_jars = {}
        self.is_private = False
    
    def enable_private_mode(self, enable):
        self.is_private = enable
        if enable:
            profile = QWebEngineProfile("PrivateMode", self)
            profile.setHttpCacheType(QWebEngineProfile.NoCache)
            profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
            profile.setCachePath("")
            profile.setPersistentStoragePath("")
        else:
            profile = QWebEngineProfile.defaultProfile()
        return profile

class GestureWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_pos = None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.start_pos:
            diff = event.pos() - self.start_pos
            if diff.x() > 50:  # 右スワイプ
                self.parent().go_back()
                self.start_pos = None
            elif diff.x() < -50:  # 左スワイプ
                self.parent().go_forward()
                self.start_pos = None
        super().mouseMoveEvent(event)

class OptimizedBrowserTab(QWidget):
    def __init__(self, parent=None, private_mode=False):
        super().__init__(parent)
        self.parent = parent
        self.private_mode = private_mode
        self.privacy_manager = PrivacyManager(self)
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
        
        # Webビュー（GestureWebViewを使用）
        self.web_view = GestureWebView()
        self.web_view.setUrl(QUrl("about:blank"))
        self.web_view.urlChanged.connect(self.update_url)
        self.web_view.titleChanged.connect(self.update_title)
        self.web_view.loadProgress.connect(self.update_progress)
        self.web_view.loadStarted.connect(self.page_load_started)
        self.web_view.loadFinished.connect(self.page_load_finished)
        self.layout.addWidget(self.web_view, stretch=1)

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False
            return re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', result.netloc)
        except ValueError:
            return False

    def safe_add_to_bookmarks(self):
        try:
            if not self.private_mode:
                self.add_to_bookmarks()
        except Exception as e:
            print(f"ブックマーク追加エラー: {e}")
            QMessageBox.critical(self, "エラー", "ブックマークの追加に失敗しました")
    
    def setup_optimizations(self):
        # プライバシーモード設定
        profile = self.privacy_manager.enable_private_mode(self.private_mode)
        
        if not self.private_mode:
            # 通常モードの最適化設定
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
            profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
            profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
            cache_path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.CacheLocation), "web_cache")
            storage_path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.DataLocation), "web_storage")
            profile.setCachePath(cache_path)
            profile.setPersistentStoragePath(storage_path)
            
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
            
        if not self.is_valid_url(url):
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                if not self.is_valid_url(url):
                    QMessageBox.warning(self, "無効なURL", "正しいURLを入力してください")
                    return
            else:
                QMessageBox.warning(self, "無効なURL", "正しいURLを入力してください")
                return
        
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
        self.setWindowTitle("Shichiha Browser")
        self.setGeometry(100, 100, 1200, 800)
        self.bookmarks = {}
        self.dark_mode = False
        self.load_bookmarks()
        self.setup_ui()
        self.setup_extensions()
    
    def safe_execute(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = f"{exc_type.__name__} in {filename}:{exc_tb.tb_lineno} - {str(e)}"
            print(f"安全実行エラー: {error_msg}")
            self.log_error(error_msg)
            return None
    
    def log_error(self, error_msg):
        log_dir = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "error_log.txt")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - {error_msg}\n")
    
    def setup_ui(self):
        # メインウィジェット
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_widget.setLayout(self.main_layout)
        
        # メニューバー
        self.setup_menu_bar()
        
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
        self.new_tab_button.clicked.connect(lambda: self.add_new_tab())
        self.tabs.setCornerWidget(self.new_tab_button)
        
        # 初期タブ
        self.add_new_tab("https://www.google.com")
        
        # ダークモード初期設定
        self.set_dark_mode(False)
    
    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル")
        
        new_tab_action = file_menu.addAction("新しいタブ")
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        
        new_window_action = file_menu.addAction("新しいウィンドウ")
        new_window_action.setShortcut("Ctrl+N")
        new_window_action.triggered.connect(self.new_window)
        
        private_tab_action = file_menu.addAction("新しいプライベートタブ")
        private_tab_action.setShortcut("Ctrl+Shift+P")
        private_tab_action.triggered.connect(lambda: self.add_new_tab(private_mode=True))
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("終了")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # 表示メニュー
        view_menu = menubar.addMenu("表示")
        
        dark_mode_action = view_menu.addAction("ダークモード")
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(lambda checked: self.set_dark_mode(checked))
        
        # 設定メニュー
        settings_menu = menubar.addMenu("設定")
        
        clear_cache_action = settings_menu.addAction("キャッシュをクリア")
        clear_cache_action.triggered.connect(self.clear_cache)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ")
        
        about_action = help_menu.addAction("バージョン情報")
        about_action.triggered.connect(self.show_about)
    
    def set_dark_mode(self, enable):
        self.dark_mode = enable
        palette = QPalette()
        if enable:
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
        else:
            palette = QApplication.style().standardPalette()
        
        self.setPalette(palette)
        
        # すべてのタブに適用
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget:
                widget.web_view.page().setBackgroundColor(palette.color(QPalette.Base))
    
    def setup_extensions(self):
        self.extensions = {}
        ext_dir = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "extensions")
        os.makedirs(ext_dir, exist_ok=True)
        
        for filename in os.listdir(ext_dir):
            if filename.endswith('.py'):
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"extension_{filename[:-3]}", os.path.join(ext_dir, filename))
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    ext = module.Extension(self)
                    self.extensions[ext.name] = ext
                except Exception as e:
                    print(f"拡張読み込みエラー {filename}: {e}")
    
    def clear_cache(self):
        reply = QMessageBox.question(self, "確認", "すべてのキャッシュをクリアしますか？",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            cache_path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.CacheLocation))
            for root, dirs, files in os.walk(cache_path):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
            QMessageBox.information(self, "完了", "キャッシュをクリアしました")
    
    def new_window(self):
        new_window = TabBrowser()
        new_window.show()
    
    def show_about(self):
        QMessageBox.about(self, "バージョン情報", 
                         "Shichiha Browser\nバージョン 1.2.1")
    
    def safe_add_bookmark(self, title, url):
        self.safe_execute(self._add_bookmark, title, url)
    
    def _add_bookmark(self, title, url):
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
    
    def setup_bookmark_bar(self):
        try:
            while self.bookmark_bar.count() > 0:
                item = self.bookmark_bar.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
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
                btn.clicked.connect(lambda checked, u=url: self.open_bookmark_safely(u))
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, b=btn: self.show_bookmark_context_menu(pos, b))
                self.bookmark_bar.addWidget(btn)
                
            self.bookmark_bar.addStretch(1)
        except Exception as e:
            print(f"ブックマークバー更新エラー: {e}")
    
    def show_bookmark_context_menu(self, pos, button):
        menu = QMenu()
        delete_action = menu.addAction("削除")
        delete_action.triggered.connect(lambda: self.remove_bookmark(button))
        menu.exec_(button.mapToGlobal(pos))
    
    def add_bookmark(self, title, url):
        self.safe_execute(self._add_bookmark, title, url)
    
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
            bookmarks_path = os.path.join(
                QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), 
                "bookmarks.json")
            
            with open(bookmarks_path, 'r', encoding='utf-8') as f:
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
        bookmarks_path = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), 
            "bookmarks.json")
        
        os.makedirs(os.path.dirname(bookmarks_path), exist_ok=True)
        with open(bookmarks_path, 'w', encoding='utf-8') as f:
            json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
    
    def add_new_tab(self, url=None, private_mode=False):
        tab = OptimizedBrowserTab(self, private_mode)
        index = self.tabs.addTab(tab, "新しいタブ" + (" (プライベート)" if private_mode else ""))
        self.tabs.setCurrentIndex(index)
        
        if url:
            tab.web_view.setUrl(QUrl(url))
        
        tab.web_view.titleChanged.connect(
            lambda title, tab=tab: self.update_tab_title(tab, title))
        
        # ダークモード適用
        if self.dark_mode:
            tab.web_view.page().setBackgroundColor(self.palette().color(QPalette.Base))
    
    def close_tab(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            widget.deleteLater()
            self.tabs.removeTab(index)
    
    def cleanup_tabs(self):
        current_index = self.tabs.currentIndex()
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget:
                if i == current_index:
                    widget.web_view.page().setVisible(True)
                    widget.web_view.setFocus()
                else:
                    widget.web_view.page().setBackgroundColor(Qt.transparent)
                    widget.web_view.page().runJavaScript("window.stop();")
                    widget.web_view.page().setVisible(False)
    
    def update_tab_title(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index != -1:
            short_title = (title[:15] + '...') if len(title) > 18 else title
            private_suffix = " (プライベート)" if tab.private_mode else ""
            self.tabs.setTabText(index, short_title + private_suffix)
            self.tabs.setTabToolTip(index, f"{title}\n{tab.web_view.url().toString()}")

    def add_bookmark_safely(self, title, url):
        self.safe_execute(self._add_bookmark, title, url)
    
    def open_bookmark_safely(self, url):
        self.safe_execute(self.open_bookmark, url)
    
    def setup_bookmark_bar(self):
        self.safe_execute(self._setup_bookmark_bar)
    
    def _setup_bookmark_bar(self):
        while self.bookmark_bar.count() > 0:
            item = self.bookmark_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
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
            btn.clicked.connect(lambda checked, u=url: self.open_bookmark_safely(u))
            self.bookmark_bar.addWidget(btn)
            
        self.bookmark_bar.addStretch(1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 高DPI対応
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # アプリケーション設定
    app.setApplicationName("Shichiha Browser")
    app.setApplicationVersion("1.2.1")
    app.setOrganizationName("GomaShichiha")
    
    browser = TabBrowser()
    browser.show()
    
    # メモリリーク防止
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(1000)
    
    sys.exit(app.exec_())
