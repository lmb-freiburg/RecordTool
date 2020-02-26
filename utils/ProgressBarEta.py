import progressbar as pb


class ProgressBarEta:
    def __init__(self, n_iter, description=""):
        self.n_iter = n_iter
        self.iter = 0
        self.description = description + ': '
        self.timer = None
        self.initialize()

    def initialize(self):
        widgets = [self.description, pb.Percentage(), ' ',
                   pb.Bar(marker=pb.RotatingMarker()), ' ', pb.ETA()]
        self.timer = pb.ProgressBar(widgets=widgets, maxval=self.n_iter).start()

    def update(self, q=1):
        if self.iter < self.n_iter:
            self.timer.update(self.iter)
            self.iter += q

    def finish(self):
        self.timer.finish()
