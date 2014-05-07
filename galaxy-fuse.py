#!/usr/bin/env python

from errno import ENOENT
from stat import S_IFDIR, S_IFREG, S_IFLNK
from sys import argv, exit
import re
import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context

from bioblend import galaxy

def path_type(path):
    parts = filter(lambda x: len(x)>0, path.split('/'))
    if path=='/':
        return ('root',dict())
    elif path=='/histories':
        return ('histories',dict())
    elif len(parts)==2 and parts[0]=='histories':
        return ('datasets',dict(h_name=unesc_filename(parts[1])))
    elif len(parts)==3 and parts[0]=='histories':
        return ('data',dict(h_name=unesc_filename(parts[1]), ds_name=unesc_filename(parts[2])))
    print "Unknown : %s"%path
    return ('',0)

# Escape/unescape slashes in filenames
def esc_filename(fname):
    def esc(m):
        c=m.group(0)
        if c=='%':
            return '%%'
        elif c=='/':
            return '%-'
    return re.sub(r'%|/', esc, fname)

def unesc_filename(fname):
    def unesc(m):
        str=m.group(0)
        if str=='%%':
            return '%'
        elif str=='%-':
            return '/'

    return re.sub(r'%(.)', unesc, fname)

class Context(LoggingMixIn, Operations):
    'Prototype FUSE to galaxy histories'

    def __init__(self, api_key):
        self.gi = galaxy.GalaxyInstance(url='http://127.0.0.1:80', key=api_key)

    def getattr(self, path, fh=None):
        #uid, gid, pid = fuse_get_context()
        (typ,kw) = path_type(path)
        now = time.time()
        if typ=='root' or typ=='histories':
            st = dict(st_mode=(S_IFDIR | 0555), st_nlink=2)
            st['st_ctime'] = st['st_mtime'] = st['st_atime'] = now
        elif typ=='datasets':
            st = dict(st_mode=(S_IFDIR | 0555), st_nlink=2)
            st['st_ctime'] = st['st_mtime'] = st['st_atime'] = now
        elif typ=='data':
            d = self._dataset(kw)
            t = time.mktime(time.strptime(d['update_time'],'%Y-%m-%dT%H:%M:%S.%f'))
            fname = esc_filename(d['file_name'])
            st = dict(st_mode=(S_IFLNK | 0444), st_nlink=1,
                              st_size=len(fname), st_ctime=t, st_mtime=t,
                              st_atime=t)
            #st = dict(st_mode=(S_IFREG | 0444), st_nlink=1,
            #                  st_size=fname, st_ctime=t, st_mtime=t,
            #                  st_atime=t)
        else:
            raise FuseOSError(ENOENT)
        return st

    def readlink(self, path):
        (typ,kw) = path_type(path)
        if typ=='data':
            d = self._dataset(kw)
            return d['file_name']
        raise FuseOSError(ENOENT)

    def read(self, path, size, offset, fh):
        raise RuntimeError('unexpected path: %r' % path)

    def _histories(self):
        return self.gi.histories.get_histories()

    def _history(self,h_name):
        h = filter(lambda x: x['name']==h_name, self.gi.histories.get_histories())
        if len(h)==0:
            raise FuseOSError(ENOENT)
        if len(h)>1:
            print "Too many histories with that name"
        return h[0]

    def _datasets(self, h):
        return self.gi.histories.show_history(h['id'],contents=True,details='all')

    def _dataset(self, kw):
        h = self._history(kw['h_name'])
        ds = self._datasets(h)
        d = filter(lambda x: x['name']==kw['ds_name'], ds)
        if len(d)==0:
            raise FuseOSError(ENOENT)
        if len(d)>1:
            print "Too many datasets with that name"
            raise FuseOSError(ENOENT)
        if 'file_name' not in d[0]:
            print "Unable to find file of dataset.  Have you set : expose_dataset_path = True"
            raise FuseOSError(ENOENT)
        return d[0]

    def readdir(self, path, fh):
        (typ,kw) = path_type(path)
        if typ=='root':
            return ['.', '..', 'histories']
        elif typ=='histories':
            hl = self._histories()
            return ['.', '..'] + [esc_filename(h['name']) for h in hl]
        elif typ=='datasets':
            h = self._history(kw['h_name'])
            ds = self._datasets(h)
            #print ds
            return ['.', '..'] + [esc_filename(d['name']) for d in ds]


    # Disable unused operations:
    access = None
    flush = None
    getxattr = None
    listxattr = None
    open = None
    opendir = None
    release = None
    releasedir = None
    statfs = None


if __name__ == '__main__':
    if len(argv) != 3:
        print('usage: %s <mountpoint> <your_api_key>' % argv[0])
        exit(1)

    fuse = FUSE(Context(argv[2]), argv[1], foreground=True, ro=True)
