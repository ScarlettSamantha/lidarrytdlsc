
def to_seconds(input: str) -> int:
    return (int(input.split(':')[0]) * 60) + int(input.split(':')[1])

def fix_viewers(input: str) -> int:
    return int(input.split(' ')[0].replace(',', ''))