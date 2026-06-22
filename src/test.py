try:
    x = 1 / 0
except Exception as e:
    from common.custom_exception import CustomException
    raise CustomException("An error occurred while performing division", error_detail=e)