from rest_framework.pagination import CursorPagination


class DefaultCursorPagination(CursorPagination):
    ordering = "id"


class ReverseCursorPagination(CursorPagination):
    ordering = "-id"
