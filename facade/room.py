from utils.router import route, MatchType as MT


@route('make room', MT.FULL_MATCH)
def make_room(cmd, ctx, *args, **kwargs):
    pass