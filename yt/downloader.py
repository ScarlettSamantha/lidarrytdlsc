
from pprint import pprint
from score import compare_video
from search import search_youtube_unofficial
from models.video import VideoData


title = "last of the wilds - Nightwish"

result = search_youtube_unofficial(title)['result']
best_result = None
best_result_score = 0.0
for vid in result:
    vid = VideoData.parse_video_data(vid)
    compare = compare_video(title, vid)
    if compare[0] > best_result_score:
        best_result_score = compare[0]
        best_result = vid
        
print(f'input: {title}')
pprint(best_result)
pprint((best_result_score, best_result))