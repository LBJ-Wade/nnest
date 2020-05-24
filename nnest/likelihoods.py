import copy
import numpy as np
from scipy.stats import multivariate_normal
import scipy.special


class Likelihood(object):
    nderived = 0

    def __init__(self, x_dim):
        self.x_dim = x_dim

    def loglike(self, x):
        if isinstance(x, list):
            x = np.array(x)
        if len(x.shape) > 1:
            return np.array([self(x) for x in x])
        else:
            return self(x)

    def sample(self, num_samples):
        max_loglike = self.max_loglike
        low, high = self.sample_range
        samples = np.empty((0, self.x_dim))
        while samples.shape[0] < num_samples:
            x = np.random.uniform(low=low, high=high, size=(1000, self.x_dim))
            loglike = self.loglike(x)
            ratio = np.exp(loglike - max_loglike)
            r = np.random.uniform(low=0, high=1, size=(1000,))
            samples = np.vstack((x[np.where(ratio > r)], samples))
        return samples[0:num_samples]

    def __call__(self, x):
        raise NotImplementedError

    def max_loglike(self):
        raise NotImplementedError

    def sample_range(self):
        raise NotImplementedError


class Rosenbrock(Likelihood):

    def __call__(self, x):
        return -sum(100.0 * (x[1:] - x[:-1] ** 2.0) ** 2.0 + (1 - x[:-1]) ** 2.0)

    @property
    def max_loglike(self):
        return self(np.ones((self.x_dim,)))

    @property
    def sample_range(self):
        return [-2] * self.x_dim, [12] * self.x_dim


class Himmelblau(Likelihood):
    x_dim = 2

    def __init__(self):
        pass

    def __call__(self, x):
        return - (x[0] ** 2 + x[1] - 11.) ** 2 - (x[0] + x[1] ** 2 - 7.) ** 2

    @property
    def max_loglike(self):
        return self([3.0, 2.0])

    @property
    def sample_range(self):
        return [-5] * self.x_dim, [5] * self.x_dim


class Gaussian(Likelihood):

    def __init__(self, x_dim, corr):
        self.corr = corr
        super(Gaussian, self).__init__(x_dim)

    def __call__(self, x):
        return multivariate_normal.logpdf(x, mean=np.zeros(self.x_dim),
                                          cov=np.eye(self.x_dim) + self.corr * (1 - np.eye(self.x_dim)))

    @property
    def max_loglike(self):
        return self([0.0] * self.x_dim)

    @property
    def sample_range(self):
        return [-5] * self.x_dim, [5] * self.x_dim


class Eggbox(Likelihood):
    x_dim = 2

    def __init__(self):
        pass

    def __call__(self, x):
        chi = (np.cos(x[0] / 2.)) * (np.cos(x[1] / 2.))
        return (2. + chi) ** 5

    @property
    def max_loglike(self):
        return self([0.0] * self.x_dim)

    @property
    def sample_range(self):
        return [-15] * self.x_dim, [15] * self.x_dim


class GaussianShell(Likelihood):

    def __init__(self, x_dim, sigma=0.1, rshell=2):
        self.sigma = sigma
        self.rshell = rshell
        super(GaussianShell, self).__init__(x_dim)

    def __call__(self, x):
        rad = np.sqrt(np.sum(x ** 2))
        return - ((rad - self.rshell) ** 2) / (2 * self.sigma ** 2)

    @property
    def max_loglike(self):
        return self(np.array([self.rshell] + [0] * (self.x_dim - 1)))

    @property
    def sample_range(self):
        return [-self.rshell - 5 * self.sigma] * self.x_dim, [self.rshell + 5 * self.sigma] * self.x_dim


def log_gaussian_pdf(theta, sigma=1, mu=0, ndim=None):
    if ndim is None:
        try:
            ndim = len(theta)
        except TypeError:
            assert isinstance(theta, (float, int)), theta
            ndim = 1
    logl = -(np.sum((theta - mu) ** 2) / (2 * sigma ** 2))
    logl -= np.log(2 * np.pi * (sigma ** 2)) * ndim / 2.0
    return logl


class GaussianMix(Likelihood):

    def __init__(self, x_dim, sep=4, weights=(0.4, 0.3, 0.2, 0.1), sigma=1):
        assert len(weights) in [2, 3, 4], ('Weights must have 2, 3 or 4 components. Weights=' + str(weights))
        assert np.isclose(sum(weights), 1), ('Weights must sum to 1! Weights=' + str(weights))
        self.sep = sep
        self.weights = weights
        self.sigma = sigma
        self.sigmas = [sigma] * len(weights)
        positions = []
        positions.append(np.asarray([0, sep]))
        positions.append(np.asarray([0, -sep]))
        positions.append(np.asarray([sep, 0]))
        positions.append(np.asarray([-sep, 0]))
        self.positions = positions[:len(weights)]
        super(GaussianMix, self).__init__(x_dim)

    def __call__(self, theta):
        thetas = []
        for pos in self.positions:
            thetas.append(copy.deepcopy(theta))
            thetas[-1][:2] -= pos
        logls = [(log_gaussian_pdf(thetas[i], sigma=self.sigmas[i])
                  + np.log(self.weights[i])) for i in range(len(self.weights))]
        return scipy.special.logsumexp(logls)

    @property
    def max_loglike(self):
        return self(self.positions[np.argmax(self.weights)])

    @property
    def sample_range(self):
        return [-self.sep - 5 * self.sigma] * self.x_dim, [self.sep + 5 * self.sigma] * self.x_dim
