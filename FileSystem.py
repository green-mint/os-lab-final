from enum import Enum
from typing import List, Union
import threading

class FileState(Enum):
    CLOSED = 0
    READ = 2
    WRITE = 3


class Node:
    # Node class
    # constructor takes a name and a parent
    def __init__(self, name: str, parent: 'Directory' = None, ):
        self.name = name
        self.parent = parent

    def get_path(self):
        if self.parent is None:
            return ""
        else:
            return self.parent.get_path() + "/" + self.name


class Directory(Node):
    def __init__(self, name: str, parent: 'Directory' = None) -> None:
        super().__init__(name, parent)
        self.children = []

    def add_child(self, child: Node):
        self.children.append(child)

    def remove_child(self, child: Node):
        self.children.remove(child)

    def get_child(self, name: str):
        for child in self.children:
            if child.name == name:
                return child
        return None


class MemoryBlock():
    """A memory block class that stores 32 characters"""

    def __init__(self, size=32):
        self.data = [""] * size
        self.file = None  # the file object that this block belongs to

    def __str__(self):
        if self.file is not None:
            return ", ".join(self.data) + " " + str(self.file.get_path()) + " " + str(len([self.data[i] for i in range(len(self.data)) if self.data[i] != ""]))
        else:
            return ", ".join(self.data) + " " + str(self.file)

    def write(self, data: str, file: 'File'):
        """Write data to the memory block"""
        self.data = list(data)
        self.file = file

    def read(self):
        """Read data from the memory block"""
        return "".join(self.data)

    def clear(self):
        """Clear the memory block"""
        self.data = [""] * len(self.data)
        self.file = None

    def is_empty(self) -> bool:
        """Check if the memory block is empty"""
        return self.file is None

    def is_occupied(self) -> bool:
        """Check if the memory block is occupied"""
        return self.file is not None


class MemoryMap():
    """
    A memory map class that stores the data of all the files as memory 
    blocks in a list. Initialize a array of memory blocks with the given block size
    """

    def __init__(self, block_size=32, num_blocks=16):
        self.block_size = block_size  # one block can store 32 characters
        # initialize num_blocks memory blocks in a list
        self.blocks: List[MemoryBlock] = [
            MemoryBlock(block_size) for i in range(num_blocks)]
        self.map = {}
    
    def add_file(self, file: 'File'):
        """Add a file to the memory map"""
        file_path = file.get_path()
        self.map[file_path] = []

    def append_file_data(self, file: 'File', data: str):
        """Append the data of a file to the memory map"""

        # split the data into blocks
        blocks = []
        for i in range(0, len(data), self.block_size):
            if i + self.block_size < len(data):
                blocks.append(data[i:i+self.block_size])
            else:
                blocks.append(data[i:])
        
        if len(blocks) == 0:
            return

        file_path = file.get_path()
        # if self.map[file_path] is None:
        #     self.map[file_path] = []
        try:
            self.map[file_path]
        except KeyError:
            raise Exception("File not found")

        # loops through self.blocks, find the empty blocks adn write the data to the blocks

        for i in range(len(self.blocks)):
            if self.blocks[i].is_empty():
                self.blocks[i].write(blocks.pop(0), file)
                self.map[file_path].append(i)
                if len(blocks) == 0:
                    break

        if len(blocks) > 0:
            raise Exception("Not enough memory to add file data")

    def truncate_file_data(self, file: 'File', size: int):
        """Truncate the data of a file to the memory map equal to the given size (num of blocks)"""
        file_path = file.get_path()
        try:
            self.map[file_path]
        except KeyError:
            raise Exception("File not found")
        if len(self.map[file_path]) < size:
            raise Exception("File size is smaller than the given size")
        # loops through self.blocks, find the empty blocks adn write the data to the blocks
        for i in range(size):
            self.blocks[self.map[file_path][(i + 1) * -1]].clear()
        self.map[file_path] = self.map[file_path][:size * -1]

    def delete_file_data(self, file: 'File'):
        file_path = file.get_path()
        try:
            self.map[file_path]
        except KeyError:
            raise Exception("File not found")
        else:
            for block_id in self.map[file_path]:
                self.blocks[block_id].clear()

    def read_file_data(self, file: 'File'):
        file_path = file.get_path()
        try:
            self.map[file_path]
        except KeyError:
            raise Exception("File not found")

        return "".join([self.blocks[block_id].read() for block_id in self.map[file_path]])

    def visualise(self):
        string = ""
        for block in self.blocks:
            string += str(block) + "\n"
        return string

class File(Node):
    def __init__(self, name: str, parent: Directory = None) -> None:
        super().__init__(name, parent)
        self.state: FileState = FileState.CLOSED
        self.readers = 0
        self.red = threading.Semaphore()
        self.write = threading.Semaphore()

    def request_read(self):
        self.red.acquire()
        self.readers = self.readers + 1

        # if atleast one reader in critical section no writer can enter (preference to readers)
        if self.readers == 1:
            self.write.acquire()
            self.mode = "r"

        self.red.release()  # other readers can enter

    def release_read(self):
        self.red.acquire()  # reader wants to leave
        self.readers = self.readers - 1

        if self.readers == 0:
            self.mode = None
            self.write.release()
            # writers can enter if no readers left in critical section

        self.red.release()  # reader leaves

    def request_write(self):
        self.write.acquire()
        self.mode = "w"

    def release_write(self):
        self.mode = None
        self.write.release()

    def open(self, mode):
        if mode not in ["r", "w"]:
            raise Exception("Invalid mode")

        if mode == "r":
            self.request_read()
            self.state = FileState.READ
        elif mode == "w":
            self.request_write()
            self.state = FileState.WRITE

    def close(self):
        if self.mode == "r":
            self.release_read()
        elif self.mode == "w":
            self.release_write()
        
        self.state = FileState.CLOSED
   
    def append(self, mmap: MemoryMap, data: str):
        if self.state != FileState.WRITE:
            raise Exception("File is not open for writing")
        else:
            mmap.append_file_data(self, data)

    def read(self, mmap: MemoryMap):
        if self.state != FileState.READ:
            raise Exception("File is not open for reading")
        else:
            return mmap.read_file_data(self)

    def truncate(self, mmap: MemoryMap, size: int):
        if self.state != FileState.WRITE:
            raise Exception("File is not open for writing")
        else:
            mmap.truncate_file_data(self, size)

    def delete(self, mmap: MemoryMap):
        mmap.delete_file_data(self)
        self.parent.remove_child(self)


class FileSystem:
    """
    Assumptions:
    - All operations will be called from the root no relative paths.
    - names ending in .[ext] will be files and without the . will be directories
    """

    def __init__(self, block_size=32, num_blocks=16):
        self.mmap = MemoryMap(block_size, num_blocks)
        self.root = Directory("/")

    def get_dir(self, path: str):

        if "." in path:
            raise Exception("Invalid path for a directory")

        if len(path) == 0:
            return self.root

        path = path.split("/")
        curr = self.root

        for name in path:
            found = False
            for child in curr.children:
                if child.name == name:
                    curr = child
                    found = True
                    break
            if not found:
                return None
        return curr

    def get_file(self, path: str) -> File or None:
        if "." not in path:
            raise Exception("Invalid path for a file")
        path = path.split("/")
        fname = path.pop()
        curr = self.root

        for name in path:
            found = False
            for child in curr.children:
                if child.name == name:
                    curr = child
                    found = True
                    break
            if not found:
                return None
        # check if file exists
        # if file does not exist return False
        for child in curr.children:
            if child.name == fname:
                return child
        return None

    def mkdir(self, path: str):
        split_path = path.split("/")
        parent_path, dname = "/".join(split_path[:-1]), split_path[-1]
        parent = self.get_dir(parent_path)
        already_exists = self.get_dir(path)
        
        if parent is None:
            raise Exception("Path does not exist.")
        if already_exists is not None:
            raise Exception("Directory already exists.")

        new_dir = Directory(dname, parent)
        parent.add_child(new_dir)
        return True

    def touch(self, path: str):
        split_path = path.split("/")
        parent_path, fname = "/".join(split_path[:-1]), split_path[-1]

        parent = self.get_dir(parent_path)
        already_exists = self.get_file(path)

        if parent is None:
            raise Exception("Path does not exist.")
        if already_exists is not None:
            raise Exception("File already exists.")
        
        new_file = File(fname, parent)
        parent.add_child(new_file)
        self.mmap.add_file(new_file)
        return True
    
    def open(self, path: str, mode="r"):
        file = self.get_file(path)

        if file is None:
            raise Exception("File does not exist.")

        file.open(mode)
        return True
    
    def close(self, path: str):
        file = self.get_file(path)

        if file is None:
            raise Exception("File does not exist.")

        file.close()
        return True

    def write(self, path: str, data: str):
        
        
        file = self.get_file(path)

        if file is None:
            raise Exception("File does not exist.")
        
        if (file.state != FileState.WRITE):
            raise Exception("File is not open for writing.")

        self.mmap.append_file_data(file, data)
        return True

    def read(self, path: str):
        file = self.get_file(path)

        if file is None:
            raise Exception("File does not exist.")
        
        if (file.state != FileState.READ):
            raise Exception("File is not open for reading.")
        
        data = self.mmap.read_file_data(file)

        return data

    def truncate(self, path: str, size: int):
        file = self.get_file(path)

        if file is None:
            raise Exception("File does not exist.")
        
        if (file.state != FileState.WRITE):
            raise Exception("File is not open for writing.")

       
        self.mmap.truncate_file_data(file, size)
   
        return True

    def delete(self, path: str):
        file = self.get_file(path)

        if file is None:
            raise Exception("File does not exist.")

        self.mmap.delete_file_data(file)
        file.parent.remove_child(file)
        return True
    
    def ls(self, path: str):
        dir = self.get_dir(path)

        if dir is None:
            raise Exception("Directory does not exist.")

        return dir.children
    
    def mv(self, src: str, dest: str):
        file = self.get_file(src)
        src_file_path = file.get_path()

        if file is None:
            raise Exception("File does not exist.")

        parent = self.get_dir(dest)
        if parent is None:
            raise Exception("Destination directory does not exist.")

        file.parent.remove_child(file)
        file.parent = parent
        parent.add_child(file)

        # change the mmap
        self.mmap.map[file.get_path()] = self.mmap.map[src_file_path]
        del self.mmap.map[src_file_path]
        return True

    def visualise_tree(self):
        """Prints the file system in a tree format"""
        def visualise_helper(node, level):
            string = "---"*level + node.name + "\n"
            # check if node is a directory
            if isinstance(node, Directory):
                for child in node.children:
                    string += visualise_helper(child, level+1)
            return string
        return visualise_helper(self.root, 0)

    def visualise_mmap(self):
        """Prints the memory map"""
        return self.mmap.visualise()

    def store_state(self):
        """Stores the state of the file system to a file"""
        def store_helper(node: Directory or File):
            if isinstance(node, Directory):
                return {
                    "type": "dir",
                    "name": node.name,
                    "path": node.get_path(),
                    "children": [store_helper(child) for child in node.children]
                }
            else:
                return {
                    "type": "file",
                    "name": node.name,
                    "path": node.get_path(),
                    "data": self.mmap.read_file_data(node)
                }
        return store_helper(self.root)
    
    def load_state(self, state):
        """Loads the state of the file system from a file"""
        def load_helper(nodes, parent):
            # pprint(node)
            for node in nodes:
                if node["type"] == "dir":
                    new_dir = Directory(node["name"], parent)
                    parent.add_child(new_dir)
                    load_helper(node["children"], new_dir)
                else:
                    new_file = File(node["name"], parent)
                    parent.add_child(new_file)
                    self.mmap.add_file(new_file)
                    self.mmap.append_file_data(new_file, node["data"])
        load_helper(state["children"], self.root)
            

# 
#     def store_state(self):
#         """Stores the state of the file system in a dictionary"""
#         def store_helper(node):
#             if node.file is None:
#                 return {
#                     "type": "dir",
#                     "name": node.name,
#                     "children": [store_helper(child) for child in node.children]
#                 }
#             else:
#                 return {
#                     "type": "file",
#                     "name": node.name,
#                     "path": node.file.path,
#                     "data": node.file.read()
#                 }
#         return store_helper(self.root)

#     def load_state(self, state):
#         """Loads the state of the file system from a dictionary"""
#         def load_helper(node, parent):
#             # pprint(node)
#             if node["type"] == "file":
#                 new_node = Node(node["name"], parent, File(
#                     node["path"], node["data"]))

#             else:
#                 new_node = Node(node["name"], parent)
#                 for child in node["children"]:
#                     load_helper(child, new_node)
#             parent.add_child(new_node)
#         self.root = Node("/", None)
#         for child in state["children"]:
#             load_helper(child, self.root)
#         self.curr = self.root


def main():
    # create file system
    fs = FileSystem()

    # fs.visualise_mmap()

    # create files
    fs.touch("a.txt")
    fs.touch("b.txt")
    fs.touch("c.txt")
    fs.mkdir("dir1")
    fs.mkdir("dir2")
    fs.mkdir("dir1/dir3")
    fs.mkdir("dir1/dir3/dir4")
    fs.mkdir("dir1/dir2")
    fs.touch("dir1/dir3/dir4/d.txt")
    fs.open("dir1/dir3/dir4/d.txt", "w")
    fs.write("dir1/dir3/dir4/d.txt", "hello world. Thsk si sme lsdjiaufh qryebf qeryfb qeryf rqoeyfbo erufb areybfqebrf eurbgfguqerbfreyfb equrfyb uqrybferuyb fgreygfb uerybf eryb fuerybf eruybf eruybf ryeubf eryubf eruyfb ruebf euryb")
    fs.open("a.txt", "w")
    fs.write("a.txt", "This is on a.txt. wihfb eryfgeyf brefwe rfgqr ekuyf gerfg ewirf gewuf ref wrefb rwefb ervf erivf eqirufv qeurfvt qeirfv qiertfv qiertfv qrefvqeriftbqeirtfv qreitfv qerfvriefv qreifv rievf iqerfvqieyrfviqeyrfv wiertfgvweirft vweirgtfv wierf")


    # fs.write("b.txt", "THis is on b.txt. jf nrgnwrotgnweorngierng wienrg oeirgn oewnwernwernvseouhgnv owehgnweohg. This is on b.txt")
    # fs.truncate("dir1/dir3/dir4/d.txt", 3)
    # fs.write("a.txt", "This is on a.txt. wihfb eryfgeyf brefwe rfgqr ekuyf gerfg ewirf gewuf ref wrefb rwefb ervf erivf eqirufv qeurfvt qeirfv qiertfv qiertfv qrefvqeriftbqeirtfv qreitfv qerfvriefv qreifv rievf iqerfvqieyrfviqeyrfv wiertfgvweirft vweirgtfv wierfv")
    # # fs.write("b.txt", "kekfwjekfbnwejfbw")
    # print(fs.read("dir1/dir3/dir4/d.txt"))

    # fs.open("a.txt", "w")

    # print(fs.open_path)

    # fs.write("hello world")

    # print(fs.read())

    print(fs.visualise_mmap())
    print(fs.visualise_tree())


if __name__ == "__main__":
    main()
