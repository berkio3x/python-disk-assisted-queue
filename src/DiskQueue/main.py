import os, sys
import marshal



class DiskQueue:

    def __init__(self, path, queue_name, cache_size, memory_safe=False):

        self.queue_name = queue_name
        self.cache_size = cache_size

        self.queue_dir = os.path.join(path, self.queue_name) 
        self.index_file = os.path.join(self.queue_dir,'000')
        
        self.get_memory_buffer = []
        self.put_memory_buffer = []

        if memory_safe:
            self.get = None
            self.put = None
        else:
            self.get  = self._get_unsafe
            self.put = self._put_unsafe

        self._init_queue()


    def _init_queue(self):

        """ If thus Queue was being operated upon previously , recover checkpoints """

        if os.path.exists(self.queue_dir):
            with open(self.index_file) as f:
                self.head , self.tail = [int(x) for x in f.read().split(',')]

        else:
            self.head, self.tail = 0,0
            os.mkdir(self.queue_dir)
            with open(self.index_file, 'w') as f:
                f.write(f"{self.head},{self.tail}")

        """ Initialize get & put memory buffers   """
        
        self._sync_from_fs_to_memory_buffer()
        

    def _sync_index_pointers(self, head, tail):
        """
        Sync the index of  head & tail pointers
        """

        with open(self.index_file, 'r+') as f:
            f.read()
            f.seek(0)
            f.write(f"{head},{tail}")

    def sync_memory_cache_to_fs(self):
        """
        Sync the cache in memory to filesystem
        """
        file_name  = os.path.join(self.queue_dir, str(self.tail))
        with open(file_name, 'wb+') as fp:
            marshal.dump(self.put_memory_buffer, fp)


    def _sync_from_fs_to_memory_buffer(self):
        """
        Sync data from fs to memory cache
        """
       
        file_name  = os.path.join(self.queue_dir, str(self.head))
        
        if os.path.exists(file_name):
            with open(file_name, 'rb') as fp:
                data  = marshal.load(fp)
                self.get_memory_buffer = data
                try:
                    os.remove(file_name)
                except Exception as e:
                    print(e)
                    print("error removing queue file {file_name} from disk")

    def __len__(self):
        """ Return the length of the queue"""

        return (self.tail - self.head)  * self.cache_size + (len(self.get_memory_buffer) \
                + len(self.put_memory_buffer))

    def _get_unsafe(self):
        
        """
        Get an object from the queue.
        """


        # Check if anything is present in the `get` memory buffer
        if self.get_memory_buffer:
            return self.get_memory_buffer.pop(0)

        else:
            # Check head & tail pointers are same
            if self.head == self.tail:
                self.get_memory_buffer = self.put_memory_buffer
                self.put_memory_buffer = []

            else:
                self._sync_from_fs_to_memory_buffer()
                self.head += 1 
                self._sync_index_pointers(self.head, self.tail)
    
        try: 
            obj = self.get_memory_buffer[0]
        except IndexError:
            obj = None
        else:
            del self.get_memory_buffer[0]
        
        return obj


    def _put_unsafe(self, obj):
        """
        Put an obj into the queue
        """
    
        if len(self.put_memory_buffer) >= self.cache_size:
            self.sync_memory_cache_to_fs()
            self.put_memory_buffer = []
            self.tail += 1
            self._sync_index_pointers(self.head, self.tail)
        self.put_memory_buffer.append(obj)
        

if __name__ == '__main__':
    import random
    dummy_data = []
    for i in range(50):
        dummy_data.append({'a':random.randint(1,2000)})

    diskQ = DiskQueue(path='./', queue_name='es-miss', cache_size=10)
    
    for obj in dummy_data:
        print(f"adding entry {obj}")
        diskQ.put(obj)

    
    print("Getting entries from queue")
    for i in range(55):
        print(diskQ.get())

