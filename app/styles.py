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

QScrollArea#sidebarScroll {
    background-color: #FFFFFF;
    border: none;
}

QScrollArea#sidebarScroll QWidget {
    background-color: #FFFFFF;
}

QLabel#navGroupLabel {
    color: #9CA3AF;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.4px;
    padding: 8px 10px 2px 10px;
}

QPushButton#navButton,
QPushButton#navButtonSoon {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #4B5563;
    font-size: 13px;
    padding: 8px 12px;
    text-align: left;
}

QPushButton#navButtonSoon {
    color: #6B7280;
}

QPushButton#navButton:hover,
QPushButton#navButtonSoon:hover {
    background-color: #F3F4F6;
    color: #111827;
}

QPushButton#navButton:checked,
QPushButton#navButtonSoon:checked {
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

QFrame#heroCard {
    background-color: #163A5F;
    border: none;
    border-radius: 16px;
}

QLabel#heroEyebrow {
    color: #93C5FD;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.6px;
}

QLabel#heroTitle {
    color: #FFFFFF;
    font-size: 28px;
    font-weight: 700;
}

QLabel#heroBody {
    color: #DBEAFE;
    font-size: 14px;
}

QLabel#heroStatus {
    color: #86EFAC;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#heroPrimaryButton {
    background-color: #2563EB;
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 600;
    min-width: 180px;
    padding: 10px 18px;
}

QPushButton#heroPrimaryButton:hover {
    background-color: #1D4ED8;
}

QPushButton#heroGhostButton {
    background-color: transparent;
    border: 1px solid #93C5FD;
    border-radius: 8px;
    color: #DBEAFE;
    font-size: 14px;
    font-weight: 600;
    min-width: 100px;
    padding: 10px 18px;
}

QPushButton#heroGhostButton:hover {
    background-color: rgba(255, 255, 255, 0.08);
}

QFrame#featureCard {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}

QLabel#featureTitle {
    color: #111827;
    font-size: 16px;
    font-weight: 700;
}

QLabel#featureText {
    color: #6B7280;
    font-size: 13px;
}

QLabel#readyBadge,
QLabel#soonBadge {
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
}

QLabel#readyBadge {
    background-color: #DCFCE7;
    color: #166534;
}

QLabel#soonBadge {
    background-color: #FEF3C7;
    color: #92400E;
}

QTableWidget#fileTable {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    color: #111827;
    font-size: 13px;
    gridline-color: #E5E7EB;
}

QTableWidget#fileTable::item {
    padding: 6px 8px;
}

QHeaderView::section {
    background-color: #F3F4F6;
    border: none;
    border-bottom: 1px solid #E5E7EB;
    border-right: 1px solid #E5E7EB;
    color: #374151;
    font-size: 12px;
    font-weight: 600;
    padding: 8px;
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
