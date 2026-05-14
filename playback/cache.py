class FrameCache1(object):

    def __init__(self, max_size=100):

        self.max_size = max_size

        self.chunks = {}

    def get(self, frame):

        return self.chunks.get(frame)

    def add(self, frame, image):
        if len(self.chunks) >= self.max_size:
            first_key = next(iter(self.chunks))
            del self.chunks[first_key]

        self.chunks[frame] = image

    def clear(self):
        self.chunks.clear()


if __name__ == "__main__":
    pass
