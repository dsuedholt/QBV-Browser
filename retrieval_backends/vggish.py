import torch
import torchaudio
import tqdm
from torch.nn.functional import cosine_similarity

import numpy as np
from numpy.linalg import norm

def get_VGGish():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = torch.hub.load('harritaylor/torchvggish', 'vggish')
    model.postprocess = True
    model.to(device)
    model.eval()

    def forward_vggish(audio):
        with torch.no_grad():
            audio = audio.numpy()[0]
            return model(audio, 16000).detach().cpu().numpy()

    return forward_vggish, 16000

def forward_audio(fwd_fun, model_sr, path):
    audio, sr = torchaudio.load(path)
    audio = torchaudio.functional.resample(audio, sr, model_sr)
    embedding = fwd_fun(audio)
    return embedding

def forward_batch(batch):
    fwd_fun, model_sr = get_VGGish()
    embeddings = {}
    for path in tqdm.tqdm(batch):
        embeddings[path] = forward_audio(fwd_fun, model_sr, path)
    return embeddings

def rank_average(item_paths, query_path, cache=None):
    fwd_fun, model_sr = get_VGGish()
    query_embedding = forward_audio(fwd_fun, model_sr, query_path).mean(0)

    # compute similarity
    similarities = {}
    for item_path in item_paths:
        if cache is not None and item_path in cache:
            item_embedding = cache[item_path].mean(0)
        else:
            item_embedding = forward_audio(fwd_fun, model_sr, item_path).mean(0)
        sim = np.dot(item_embedding, query_embedding) / (norm(item_embedding)*norm(query_embedding))
        similarities[item_path] = sim.item()
    return similarities

def rank_align(item_paths, query_path, cache=None):
    fwd_fun, model_sr = get_VGGish()
    query_embedding = forward_audio(fwd_fun, model_sr, query_path)

    def match_sequences(a, b):
        if len(a) <= len(b):
            a, b = b, a
        hops = len(a) - len(b)

        mses = []
        for i in range(hops+1):
            mses.append(((a[i:i + len(b)] - b) ** 2).mean())
        return np.min(mses) * -1

    # compute similarity
    similarities = {}
    for item_path in item_paths:
        if cache is not None and item_path in cache:
            item_embedding = cache[item_path]
        else:
            item_embedding = forward_audio(fwd_fun, model_sr, item_path)

        sim = match_sequences(item_embedding, query_embedding)
        similarities[item_path] = sim.item()
    return similarities