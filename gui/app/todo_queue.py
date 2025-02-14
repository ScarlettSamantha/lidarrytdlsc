class todo_queue():
    
    def __init__(self):
        self.items = []
        
    def __repr__(self) -> str:
        return f'Contains {int(self.items.__len__())}'