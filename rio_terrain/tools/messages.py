import sys

# Startup information
STARTING = "Running {} on {}"
INMEMORY = "in-memory raster"
SEQUENTIAL = "sequential raster blocks"
CONCURRENT = "concurrent raster blocks"

# Completion status
COMPLETION = "Finished in {}"
WRITEOUT = "Wrote output to {}"

# Warnings
STRIPED = 'Blocks are lines with shape {}. Rewrite the data blocks for faster out-of-core processing.'

# Errors
NONINTERSECTING = 'Input rasters are non-intersecting'
NONALIGNED = 'Raster cells are not aligned between inputs'


def printtime(t0, t1):
    '''Return the elapsed time between t0 and t1 in h:m:s formatted string

    '''
    m, s = divmod(t1 - t0, 60)
    h, m = divmod(m, 60)
    fmt = '%d:%02d:%02d' % (h, m, s)

    return fmt


def progress(value, endvalue, bar_length=20, msg=None):
    """Display and update a progress bar

    """
    done_char = '#'
    todo_char = ' '

    percent = float(value) / endvalue
    progress = done_char * int(round(percent * bar_length))
    spaces = todo_char * (bar_length - len(progress))

    message = "\rPercent: [{0}] {1}%    {2}".format(progress + spaces, int(round(percent * 100)), msg)
    sys.stdout.write(message)
    if value == endvalue-1:
        sys.stdout.write('\n')
    sys.stdout.flush()
