from torchvision import transforms
import torch
from torch.utils.data import dataset, dataloader
from torchvision.datasets.folder import default_loader
from utils.RandomErasing import RandomErasing
from utils.RandomSampler import RandomSampler
# from utils.Sampler import Sampler
from opt import opt
import os
import re
import cv2

class Data():
    def __init__(self):
        train_transform = transforms.Compose([
            transforms.Resize((384, 128), interpolation=3),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            RandomErasing(probability=0.5, mean=[0.0, 0.0, 0.0])
        ])
        train_transform_woEr = transforms.Compose([
            transforms.Resize((384, 128), interpolation=3),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])


        test_transform = transforms.Compose([
            transforms.Resize((384, 128), interpolation=3),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        self.trainset = PRCC(train_transform, 'train', opt.data_path)
        self.trainset_woEr = PRCC(train_transform_woEr, 'train', opt.data_path)
        self.testset = PRCC(test_transform, 'test', opt.data_path)
        self.queryset = PRCC(test_transform, 'query', opt.data_path)

        self.train_loader = dataloader.DataLoader(
            self.trainset, 
            sampler=RandomSampler(self.trainset, batch_id=opt.batchid,batch_image=opt.batchimage),
            batch_size=opt.batchid * opt.batchimage, num_workers=8, pin_memory=True)
        
        self.train_loader_woEr = dataloader.DataLoader(
            self.trainset_woEr,
            sampler=RandomSampler(self.trainset_woEr, batch_id=opt.batchid, batch_image=opt.batchimage),
            batch_size=opt.batchid * opt.batchimage, num_workers=8, pin_memory=True)

        self.test_loader = dataloader.DataLoader(
            self.testset, batch_size=opt.batchtest, num_workers=8, pin_memory=True)
        self.query_loader = dataloader.DataLoader(
            self.queryset, batch_size=opt.batchtest, num_workers=8, pin_memory=True)

class PRCC(dataset.Dataset):
    def __init__(self, transform, dtype, data_path):

        self.train_transform_gray = transforms.Compose([
            transforms.Grayscale(num_output_channels=1),
            transforms.Resize((384, 128), interpolation=3),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485], std=[0.229])
        ])

        self.transform = transform
        self.loader = default_loader
        self.rgb_data_path = data_path + '/rgb'
        self.sketch_data_path = data_path + '/sketch'

        if dtype == 'train':
            self.rgb_data_path += '/bounding_box_train'
            self.sketch_data_path += '/bounding_box_train'
        elif dtype == 'test':
            self.rgb_data_path += '/bounding_box_test'
            self.sketch_data_path += '/bounding_box_test'
        else:
            self.rgb_data_path += '/query'
            self.sketch_data_path += '/query'

        self.imgs = [path for path in self.list_pictures(self.rgb_data_path) if self.id(path) != -1]
        self.sketch = [path for path in self.list_pictures(self.sketch_data_path) if self.id(path) != -1]

        self._id2label = {_id: idx for idx, _id in enumerate(self.unique_ids)}

    def __getitem__(self, index):
        rgb_path = self.imgs[index]
        sketch_path = self.sketch[index]
        # if rgb_path[-17:] != sketch_path[-17:]:
            # print('yes')
        target = self._id2label[self.id(rgb_path)]

        img = self.loader(rgb_path)
        # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sketch = self.loader(sketch_path)
        if self.transform is not None:
            gray = self.train_transform_gray(img)
            img = self.transform(img)
            sketch = self.transform(sketch)

        return img, sketch, gray, target

    def __len__(self):
        return len(self.imgs)

    @staticmethod
    def id(file_path):
        """
        :param file_path: unix style file path
        :return: person id
        """
        return int(file_path.split("\\")[-1].split('_')[0])

    @staticmethod
    def camera(file_path):
        """
        :param file_path: unix style file path
        :return: camera id
        """
        return int(file_path.split('\\')[-1].split('_')[1][1])

    @property
    def ids(self):
        """
        :return: person id list corresponding to dataset image paths
        """
        return [self.id(path) for path in self.imgs]

    @property
    def unique_ids(self):
        """
        :return: unique person ids in ascending order
        """
        return sorted(set(self.ids))

    @property
    def cameras(self):
        """
        :return: camera id list corresponding to dataset image paths
        """
        return [self.camera(path) for path in self.imgs]

    @staticmethod
    def list_pictures(directory, ext='jpg|jpeg|bmp|png|ppm|npy'):
        assert os.path.isdir(directory), 'dataset is not exists!{}'.format(directory)

        return sorted([os.path.join(root, f)
                       for root, _, files in os.walk(directory) for f in files
                       if re.match(r'([\w]+\.(?:' + ext + '))', f) ])
