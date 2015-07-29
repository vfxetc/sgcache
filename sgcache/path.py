import collections


_FieldPathSegment = collections.namedtuple('FieldPathSegment', 'type field')
class FieldPathSegment(_FieldPathSegment):
    
    """One segment of a :class:`FieldPath`.

    .. attribute:: type

        The entity type of this segment.

    .. attribute:: field

        The field name of this segment.

    """

    def __str__(self):
        return '%s.%s' % self


class FieldPath(collections.Sequence):

    """A path in an API3 filter or return field; a sequence of
    :class:`FieldPathSegment` objects.

    :param input: A list of :class:`FieldPathSegment`, or a string.
    :param root_type: The entity type this field starts at; required if
        the input is a string.

    ::

        >>> path = FieldPath('entity.Shot.sg_sequence.Sequence.code', root_type='Task')

        >>> str(path)
        'entity.Shot.sg_sequence.Sequence.code'

        >>> str(path[:1])
        'entity'
        
        >>> str(path[1:])
        'sg_sequence.Sequence.code'

    """

    def __init__(self, input_, root_type=None):

        if isinstance(input_, basestring):
            assert root_type
            parts = input_.split('.')
            self.segments = segments = [FieldPathSegment(root_type, parts.pop(0))]
            while parts:
                segments.append(FieldPathSegment(parts.pop(0), parts.pop(0)))
        else:
            self.segments = input_[:]

    def __len__(self):
        return len(self.segments)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return FieldPath(self.segments[index])
        else:
            return self.segments[index]

    def format(self, head=False, tail=True, _cached=True):
        """Stringify this path.

        :param bool head: Include the root entity type?
        :param bool tail: Include the final field name?

        ::

            >>> path = FieldPath('entity.Shot.code', root_type='Task')

            >>> path.format()
            'entity.Shot.code'

            >>> path.format(head=True)
            'Task.entity.Shot.code'

            >>> path.format(tail=False)
            'entity.Shot'

        """

        # If this is the very common case, cache it the first time.
        # Doing this results in cutting down 2/3 of the time to respond to
        # read queries that return 500 entities.
        if tail and not head and _cached:
            try:
                return self._format_cache
            except AttributeError:
                res = self._format_cache = self.format(_cached=False)
                return res

        len_ = len(self)

        if not len_:
            return ''

        if len_ == 1:
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
        if len_ > 1:
            parts.extend('%s.%s' % x for x in self[1:-1])
            parts.append(('%s.%s' % self[-1]) if tail else self[-1][0])

        return '.'.join(parts)

    def __str__(self):
        return self.format()

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self)
