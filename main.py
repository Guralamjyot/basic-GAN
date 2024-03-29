import os
import random
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim as optim
import torch.utils.data

import torchvision.datasets as datasets
import torchvision.transforms as transforms
import torchvision.utils as visionutils
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from IPython.display import HTML


batch_size = 64
image_size = 64
nc = 3
nz = 1000
ngf = 64
ndf = 64
num_epochs = 10

lr = 0.0002
z_vec=1000
num_epochs=50
lr=2e-4
device=torch.device('cuda' if torch.cuda.is_available else 'cpu')
fixed_noise = torch.randn(64, 1000, 1, 1, device=device)

dataset = datasets.ImageFolder(root='hui',
                           transform=transforms.Compose([
                               transforms.Resize(image_size),
                               transforms.CenterCrop(image_size),
                               transforms.ToTensor(),
                               transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
                           ]))
data=torch.utils.data.DataLoader(dataset,batch_size=batch_size,shuffle=True)

""" batch=next(iter(data))
plt.figure(figsize=(10,10))
plt.axis('off')
plt.imshow(np.transpose(visionutils.make_grid(batch[0].to(device)[:64], padding=2, normalize=True).cpu(),(1,2,0)))
plt.show() """


def weight_init(m):
    classname=m.__class__.__name__
    if classname.find('Conv')!= -1:
        nn.init.normal_(m.weight.data,0.0,0.02)

    elif classname.find('BatchNorm')!= -1:
        nn.init.normal_(m.weight.data,1.0,0.02)
        nn.init.constant_(m.bias.data,0)

class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.main = nn.Sequential(
            # input is Z, going into a convolution
            nn.ConvTranspose2d( nz, ngf * 8, 4, 1, 0, bias=False),
            nn.BatchNorm2d(ngf * 8),
            nn.ReLU(True),
            # state size. ``(ngf*8) x 4 x 4``
            nn.ConvTranspose2d(ngf * 8, ngf * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 4),
            nn.ReLU(True),
            # state size. ``(ngf*4) x 8 x 8``
            nn.ConvTranspose2d( ngf * 4, ngf * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 2),
            nn.ReLU(True),
            # state size. ``(ngf*2) x 16 x 16``
            nn.ConvTranspose2d( ngf * 2, ngf, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf),
            nn.ReLU(True),
            # state size. ``(ngf) x 32 x 32``
            nn.ConvTranspose2d( ngf, nc, 4, 2, 1, bias=False),
            nn.Tanh()
            # state size. ``(nc) x 64 x 64``
        )
        
    def forward(self,input):
        return self.main(input)

class Discriminator(nn.Module):

    def __init__(self):
        super().__init__()
        self.main = nn.Sequential(
            # input is ``(nc) x 64 x 64``
            nn.Conv2d(nc, ndf, 4, 2, 1, bias=False),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. ``(ndf) x 32 x 32``
            nn.Conv2d(ndf, ndf * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 2),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. ``(ndf*2) x 16 x 16``
            nn.Conv2d(ndf * 2, ndf * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 4),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. ``(ndf*4) x 8 x 8``
            nn.Conv2d(ndf * 4, ndf * 8, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 8),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. ``(ndf*8) x 4 x 4``
            nn.Conv2d(ndf * 8, 1, 4, 1, 0, bias=False),
            nn.Sigmoid()
        )

    def forward(self,input):
        return self.main(input)
        
netG=Generator().to(device)
netD=Discriminator().to(device)

netG.apply(weight_init)
netD.apply(weight_init)

criterion=nn.BCELoss()
real_label=1
fake_label=0

optimizerD=optim.Adam(netD.parameters(),lr=lr,betas=(0.5,0.999))
optimizerG=optim.Adam(netG.parameters(),lr=lr,betas=(0.5,0.999))

img_list=[]
G_losses=[]
D_losses=[]
iters=0
 
""" for epoch in range(num_epochs):
    for i,batch in enumerate(data,0):
        netD.zero_grad()
        real=batch[0].to(device)
        b_size=real.size(0)
        label=torch.full((b_size,),real_label,dtype=torch.float,device=device)
        output=netD(real).view(-1)
        errD_real=criterion(output,label)
        errD_real.backward()
        D_x=output.mean().item()

        noise=torch.randn(b_size,1000,1,1,device=device)
        fake=netG(noise)
        label.fill_(fake_label)
        output=netD(fake.detach()).view(-1)
        errD_fake=criterion(output,label)

        errD_fake.backward()
        DGz1=output.mean().item()
        optimizerD.step()

        errD=errD_fake+errD_real


        netG.zero_grad()
        label.fill_(real_label)

        output=netD(fake).view(-1)
        errG=criterion(output,label)
        errG.backward()
        DGz2=output.mean().item()
        optimizerG.step()

        if i%50==0:
            print(i,'th iteration of ',epoch,'out of ',num_epochs)
            G_losses.append(errG.item())
            D_losses.append(errD.item())


        if (iters % 500 == 0) or ((epoch == num_epochs-1) and (i == len(data)-1)):
            with torch.no_grad():
                fake=netG(fixed_noise).detach().cpu()
                img_list.append(visionutils.make_grid(fake,padding=2,normalize=True))
            
        iters+=1
torch.save(netD.state_dict(),'bestD.pt')
torch.save(netG.state_dict(),'bestG.pt') """

netD.load_state_dict(torch.load('bestD.pt'))
netG.load_state_dict(torch.load('bestG.pt'))
netD.to(device)
netG.to(device)

for i in range(10):
    with torch.no_grad():
        noise=torch.randn(batch_size,1000,1,1,device=device)
        fake=netG(noise).detach().cpu()
        img_list.append(visionutils.make_grid(fake,padding=2,normalize=True))
        


fig = plt.figure(figsize=(8,8))
plt.axis("off")
ims = [[plt.imshow(np.transpose(i,(1,2,0)), animated=True)] for i in img_list]
ani = animation.ArtistAnimation(fig, ims, interval=1000, repeat_delay=1000, blit=True)
HTML(ani.to_jshtml())
plt.show()