# Galaxy-FUSE
### Make galaxy history files available via a FUSE layer

This will create a read-only directory to view the files in your galaxy histories.  At the moment this is implemented using symlinks to the actual data-set files

### Requirements

* pip install --user bioblend
* pip install --user fusepy
* mkdir galaxy-files
* edit your galaxy galaxy_wsgi.ini file, and add to the following to the app:main section `expose_dataset_path = True`

Then run:

    ./galaxy-fuse.py galaxy-files <your_api_key>


### Limitations

* Read-only access
* Histories or data-sets with non-unique names will not work
* No caching of history lookup (ie. stat() call), so can be slow-ish.  Caching should be easy to add
* History or data-set names containg a slash (/) are escaped to '%-'
