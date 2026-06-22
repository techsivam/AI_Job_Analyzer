import sys

class CustomException(Exception):
    def __init__(self, message: str, error_detail:Exception=None):
        self.error_message = self.get_detailed_error_message(message, error_detail=error_detail)
        super().__init__(message)
    @staticmethod
    def get_detailed_error_message(message: str, error_detail:Exception=None) -> str:
        _, _, exc_tb = sys.exc_info()
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno
        return (
            f"message: {message} | "
            f"Error : {str(error_detail)} | "
            f"File Name: {file_name} | "
            f"Line Number: {line_number}"
        )
       

    def __str__(self):
        return self.error_message