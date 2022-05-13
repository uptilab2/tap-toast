
class Context:
    config = {}

    @staticmethod
    def update(state, stream_id):
        if state and 'bookmarks' in state and stream_id in state['bookmarks']:
            stream = state['bookmarks'][stream_id]
            for key in stream:
                if key in Context.config:
                    Context.config[key] = stream[key]
                else:
                    Context.config.update({key: stream[key]})
