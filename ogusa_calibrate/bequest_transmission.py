import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import kde
import os
import ogusa  # import just for MPL style file


# Will need to do some smoothing with a KDE when estimate the matrix...
def MVKDE(S, J, proportion_matrix, filename=None, plot=False, bandwidth=.25):
    '''
    Generates a Multivariate Kernel Density Estimator and returns a
    matrix representing a probability distribution according to given
    age categories, and ability type categories.

    Args:
        S (scalar): the number of age groups in the model
        J (scalar): the number of ability type groups in the model.
        proportion_matrix (Numpy array): SxJ shaped array that
            represents the proportions of the total going to each
            (s,j) combination
        filename (str): the file name  to save image to
        plot (bool): whether or not to save a plot of the probability
            distribution generated by the kde or the proportion matrix
        bandwidth (scalar):  used in the smoothing of the kernel. Higher
            bandwidth creates a smoother kernel.

    Returns:
        estimator_scaled (Numpy array): SxJ shaped array that
            that represents the smoothed distribution of proportions
            going to each (s,j)

    '''
    proportion_matrix_income = np.sum(proportion_matrix, axis=0)
    proportion_matrix_age = np.sum(proportion_matrix, axis=1)
    age_probs = np.random.multinomial(70000, proportion_matrix_age)
    income_probs = np.random.multinomial(70000, proportion_matrix_income)
    age_frequency = np.array([])
    income_frequency = np.array([])
    age_mesh = complex(str(S) + 'j')
    income_mesh = complex(str(J) + 'j')
    j = 18
    '''creating a distribution of age values'''
    for i in age_probs:
        listit = np.ones(i)
        listit *= j
        age_frequency = np.append(age_frequency, listit)
        j += 1

    k = 1
    '''creating a distribution of ability type values'''
    for i in income_probs:
        listit2 = np.ones(i)
        listit2 *= k
        income_frequency = np.append(income_frequency, listit2)
        k += 1

    freq_mat = np.vstack((age_frequency, income_frequency)).T
    density = kde.gaussian_kde(freq_mat.T, bw_method=bandwidth)
    age_min, income_min = freq_mat.min(axis=0)
    age_max, income_max = freq_mat.max(axis=0)
    agei, incomei = np.mgrid[age_min:age_max:age_mesh,
                             income_min:income_max:income_mesh]
    coords = np.vstack([item.ravel() for item in [agei, incomei]])
    estimator = density(coords).reshape(agei.shape)
    estimator_scaled = estimator/float(np.sum(estimator))
    if plot:
        fig = plt.figure()
        ax = fig.gca(projection='3d')
        ax.plot_surface(agei,incomei, estimator_scaled, rstride=5)
        ax.set_xlabel("Age")
        ax.set_ylabel("Ability Types")
        ax.set_zlabel("Received proportion of total bequests")
        plt.savefig(filename)
    return estimator_scaled


def get_bequest_matrix(graphs=False):
    '''
    Returns S x J matrix representing the fraction of aggregate
    bequests that go to each household by age and lifetime income group.

    '''
    # Create directory if output directory does not already exist
    cur_path = os.path.split(os.path.abspath(__file__))[0]
    output_fldr = 'csv_output_files'
    output_dir = os.path.join(cur_path, output_fldr)
    if not os.access(output_dir, os.F_OK):
        os.makedirs(output_dir)
    image_fldr = 'images'
    image_dir = os.path.join(cur_path, image_fldr)
    if not os.access(image_dir, os.F_OK):
        os.makedirs(image_dir)

    # Define a lambda function to compute the weighted mean:
    # wm = lambda x: np.average(
    #     x, weights=df.loc[x.index, "fam_smpl_wgt_core"])

    # Read in dataframe of PSID data
    df = ogusa.utils.safe_read_pickle(os.path.join(
        cur_path, 'data', 'PSID', 'psid_lifetime_income.pkl'))

    # Do some tabs with data file...
    # 'net_wealth', 'inheritance', 'value_inheritance_1st',
    # 'value_inheritance_2nd', 'value_inheritance_3rd's
    # inheritance available from 1988 onwards...
    # Note that the resulting distribution is very different from what
    # Rick has found with the SCF

    df['sum_inherit'] = (
        df['value_inheritance_1st'] + df['value_inheritance_2nd'] +
        df['value_inheritance_3rd'])
    # print(df[['sum_inherit', 'inheritance']].describe())

    if graphs:
        # Total inheritances by year
        df.groupby('year_data').mean().plot(y='inheritance')
        plt.savefig(os.path.join(image_dir, 'inheritance_year.png'))
        df.groupby('year_data').mean().plot(y='sum_inherit')
        plt.savefig(os.path.join(image_dir, 'sum_inherit_year.png'))
        # not that summing up inheritances gives a much larger value than
        # taking the inheritance variable

        # Fraction of inheritances in a year by age
        # line plot
        df[df['year_data'] >= 1988].groupby('age').mean().plot(y='net_wealth')
        plt.savefig(os.path.join(image_dir, 'net_wealth_age.png'))
        df[df['year_data'] >= 1988].groupby('age').mean().plot(y='inheritance')
        plt.savefig(os.path.join(image_dir, 'inheritance_age.png'))

        # Inheritances by lifetime income group
        # bar plot
        df[df['year_data'] >= 1988].groupby('li_group').mean().plot.bar(
            y='net_wealth')
        plt.savefig(os.path.join(image_dir, 'net_wealth_li.png'))
        df[df['year_data'] >= 1988].groupby('li_group').mean().plot.bar(
            y='inheritance')
        plt.savefig(os.path.join(image_dir, 'inheritance_li.png'))

        # lifecycle plots with line for each ability type
        pd.pivot_table(df[df['year_data'] >= 1988], values='net_wealth', index='age',
                    columns='li_group', aggfunc='mean').plot(legend=True)
        plt.savefig(os.path.join(image_dir, 'net_wealth_age_li.png'))
        pd.pivot_table(df[df['year_data'] >= 1988], values='inheritance', index='age',
                    columns='li_group', aggfunc='mean').plot(legend=True)
        plt.savefig(os.path.join(image_dir, 'inheritance_age_li.png'))

    # Matrix Fraction of inheritances in a year by age and lifetime_inc
    inheritance_matrix = pd.pivot_table(
        df[df['year_data'] >= 1988], values='inheritance', index='age',
        columns='li_group', aggfunc='sum')
    # replace NaN with zero
    inheritance_matrix.fillna(value=0, inplace=True)
    inheritance_matrix = inheritance_matrix / inheritance_matrix.sum().sum()
    # inheritance_matrix.to_csv(os.path.join(
    #     output_dir, 'bequest_matrix.csv'))

    # estimate kernel density of bequests
    kde_matrix = MVKDE(
        80, 7, inheritance_matrix.to_numpy(),
        filename=os.path.join(image_dir, 'inheritance_kde.png'), plot=graphs,
        bandwidth=.5)
    np.savetxt(os.path.join(
        output_dir, 'bequest_matrix_kde.csv'), kde_matrix, delimiter=",")

    return kde_matrix