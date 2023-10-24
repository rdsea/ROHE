



from .restful_service_module import ServiceController


class IngestionServiceController(ServiceController):
    def __init__(self, config):
        super().__init__(config)

    def get_command_handler(self, request):
        return super().get_command_handler(request)
    
    def post_command_handler(self, request):
        return super().post_command_handler(request)
    
    def put_command_handler(self, request):
        return super().put_command_handler(request)
    
    def delete_command_handler(self, request):
        return super().delete_command_handler(request)