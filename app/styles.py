APP_STYLESHEET = """
QMainWindow {
    background-color: #F4F6F8;
}

QWidget#centralWidget {
    background-color: #F4F6F8;
}

QWidget#sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E7EB;
}

QLabel#brandTitle {
    color: #111827;
    font-size: 16px;
    font-weight: 700;
}

QLabel#brandSubtitle {
    color: #6B7280;
    font-size: 12px;
}

QLabel#sidebarFooter {
    color: #9CA3AF;
    font-size: 11px;
}

QPushButton#navButton {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #4B5563;
    font-size: 14px;
    padding: 10px 14px;
    text-align: left;
}

QPushButton#navButton:hover {
    background-color: #F3F4F6;
    color: #111827;
}

QPushButton#navButton:checked {
    background-color: #E8F0FE;
    color: #1D4ED8;
    font-weight: 600;
}

QWidget#contentArea {
    background-color: #F4F6F8;
}

QWidget#page {
    background-color: transparent;
}

QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}

QLabel#pageTitle {
    color: #111827;
    font-size: 28px;
    font-weight: 700;
}

QLabel#pageSubtitle {
    color: #6B7280;
    font-size: 15px;
}

QLabel#statusText {
    color: #047857;
    font-size: 14px;
    font-weight: 600;
}

QLabel#placeholderTitle {
    color: #111827;
    font-size: 22px;
    font-weight: 700;
}

QLabel#placeholderText {
    color: #6B7280;
    font-size: 14px;
}

QPushButton#primaryButton {
    background-color: #2563EB;
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 600;
    min-width: 120px;
    padding: 10px 20px;
}

QPushButton#primaryButton:hover {
    background-color: #1D4ED8;
}

QPushButton#primaryButton:pressed {
    background-color: #1E40AF;
}

QPushButton#secondaryButton {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    color: #111827;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 12px;
}

QPushButton#secondaryButton:hover {
    background-color: #F3F4F6;
}

QPushButton#dangerButton {
    background-color: #FFFFFF;
    border: 1px solid #FECACA;
    border-radius: 8px;
    color: #B91C1C;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 12px;
}

QPushButton#dangerButton:hover {
    background-color: #FEF2F2;
}

QLabel#sectionTitle {
    color: #111827;
    font-size: 16px;
    font-weight: 700;
}

QLabel#pathLabel {
    color: #374151;
    font-size: 12px;
}

QLabel#hintText {
    color: #6B7280;
    font-size: 12px;
}

QListWidget#fileList,
QTreeView#folderTree {
    background-color: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    color: #111827;
    font-size: 13px;
    padding: 4px;
}

QListWidget#fileList::item,
QTreeView#folderTree::item {
    padding: 4px 6px;
}

QSplitter::handle {
    background-color: transparent;
    width: 12px;
}

QMessageBox {
    background-color: #FFFFFF;
}

QMessageBox QLabel {
    color: #111827;
    font-size: 13px;
}
"""
