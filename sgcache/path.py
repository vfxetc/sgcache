import collections


_PathSegment = collections.namedtuple('PathSegment', 'type field')
class PathSegment(_PathSegment):

    def __str__(self):
        return '%s.%s' % self


class Path(collections.Sequence):

    def __init__(self, input_, root_type=None):
        if isinstance(input_, basestring):
            assert root_type
            parts = input_.split('.')
            self.segments = segments = [PathSegment(root_type, parts.pop(0))]
            while parts:
                segments.append(PathSegment(parts.pop(0), parts.pop(0)))
        else:
            self.segments = input_[:]

    def __len__(self):
        return len(self.segments)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return Path(self.segments[index])
        else:
            return self.segments[index]

    def format(self, head=False, tail=True):

        if len(self) == 1:
            if head and tail:
                return '%s.%s' % self[0]
            elif head:
                return self[0][0]
            elif tail:
                return self[0][1]
            else:
                raise ValueError('need head or tail when single-element path')

        parts = []
        parts.append(('%s.%s' % self[0]) if head else self[0][1])
        if len(self) > 1:
            parts.extend('%s.%s' % x for x in self[1:-1])
            parts.append(('%s.%s' % self[-1]) if tail else self[-1][0])
        return '.'.join(parts)

    def __str__(self):
        return self.format()
