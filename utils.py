import logging

logger = logging.getLogger(__name__)

def format_file_size(bytes_size: int) -> str:
    """
    Форматирует размер файла в читаемый вид.
    
    Args:
        bytes_size: Размер в байтах
        
    Returns:
        Строка с отформатированным размером (B, KB, MB, GB)
    """
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size/1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size/(1024*1024):.1f} MB"
    else:
        return f"{bytes_size/(1024*1024*1024):.1f} GB"
