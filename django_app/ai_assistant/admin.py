from django.contrib import admin
from .models import Chat, Message

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'ai_name',
        'isActived',
        'isDeleted',
        'dateTime',
        'model',
    )
    list_filter = ('isActived', 'isDeleted', 'model')
    search_fields = ('title', 'ai_name', 'description', 'capabilities', 'personality')
    ordering = ('-dateTime',)
    fieldsets = (
        (None, {
            'fields': ('title', 'ai_name', 'description', 'capabilities', 'personality', 'model', 'context')
        }),
        ('Status', {
            'fields': ('isActived', 'isDeleted')
        }),
        ('Date Information', {
            'fields': ('dateTime',)
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.order_by('-dateTime')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'role', 'content', 'timestamp')  # Updated field names
    list_filter = ('role', 'timestamp')
    search_fields = ('content',)

# admin.site.register(Message, MessageAdmin)

