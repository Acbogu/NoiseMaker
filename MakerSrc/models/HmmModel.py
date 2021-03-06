import tensorflow as tf


class HmmModel(object):

    def __init__(self, transfer, emission, pi):
        """
        定义HMM模型
        :param transfer: 状态转移矩阵
        :param emission: 观测矩阵
        :param pi: 初始状态向量
        """
        self.st_num = transfer.shape[0]  # 状态数量
        self.ob_num = emission.shape[0]  # 观测值数量

        self.E = tf.get_variable('emission', initializer=emission)  # 输出矩阵
        self.T = tf.get_variable('transfer', initializer=transfer)  # 转移矩阵
        self.T0 = tf.get_variable('pi', dtype=tf.float64, initializer=pi)  # 初始状态向量

    def define_viterbi(self, ob_seq, length):
        """
        Viterbi算法
        :param length: 观测序列的长度
        :param ob_seq: 观测序列
        :return: 该观测序列的隐含状态列表及其概率
        """
        # ob_seq = tf.constant(seq, dtype=tf.int32)  # 观测序列

        path_states = tf.get_variable('states_matrix', dtype=tf.int64, shape=[length, self.st_num], initializer=tf.zeros_initializer())  # 每个时间步长的隐含状态
        path_scores = tf.get_variable('score_matrix', dtype=tf.float64, shape=[length, self.st_num], initializer=tf.zeros_initializer())  # 每个时间步长的分数
        st_seq = tf.get_variable('states_sequence', dtype=tf.int64, shape=[length], initializer=tf.zeros_initializer())  # 隐含状态序列
        ob_prob_seq = tf.log(tf.gather(self.E, ob_seq))  # 每个观测状态的可能性矩阵 （对概率取对数）
        ob_prob_list = tf.split(ob_prob_seq, length, axis=0)
        path_scores = tf.scatter_update(path_scores, 0, tf.log(self.T0) + tf.squeeze(ob_prob_list[0]))  # 第一个时间步长各个状态的概率取对数

        for step, ob_prob in enumerate(ob_prob_list[1:]):
            scores_reshape = tf.reshape(path_scores[step, :], (-1, 1))
            belief = tf.add(scores_reshape, tf.log(self.T))  # 下一个时间步长出现各个隐含状态的概率（取对数）
            path_states = tf.scatter_update(path_states, step + 1, tf.argmax(belief, 0))
            path_scores = tf.scatter_update(path_scores, step + 1, tf.reduce_max(belief, 0) + tf.squeeze(ob_prob))
        st_seq = tf.scatter_update(st_seq, length - 1, tf.argmax(path_scores[length - 1, :], 0))  # 最后一个时间步长的状态

        for step in range(length - 1, 0, -1):
            state = st_seq[step]
            idx = tf.reshape(tf.stack([step, state]), [1, -1])
            state_prob = tf.gather_nd(path_states, idx)
            st_seq = tf.scatter_update(st_seq, step - 1, state_prob[0])
        self._state_seq = st_seq  # 各个时间步长的状态
        self._state_prob = tf.exp(path_scores)  # 各个时间步长的概率

    @property
    def state_seq(self):
        return self._state_seq

    @property
    def state_prob(self):
        return self._state_prob


class ForwardModel(object):

    def __init__(self, transfer, emission, hidden_state_num, ob_seq_len):
        """
        定义HMM模型
        :param transfer: 状态转移矩阵
        :param emission: 观测矩阵
        """
        # 1.定义一些变量
        self.st_num = transfer.shape[0]  # 状态数量
        self.ob_num = emission.shape[0]  # 观测值数量
        self.pi = tf.placeholder(shape=[hidden_state_num], dtype=tf.float64)  # 初始概率
        self.ob_seq = tf.placeholder(shape=[ob_seq_len], dtype=tf.int32)  # 观测序列
        # 2.第一步观测
        obs_status = tf.gather(self.ob_seq, 0)  # 观测序列的第一个值
        alpha = tf.multiply(self.pi, tf.gather(emission, obs_status))  # 隐含层为某一个值 且输出了一个特定状态的概率
        # 3.前向地推
        for step in range(1, ob_seq_len):
            obs_status = tf.gather(self.ob_seq, step)
            prev_prob = tf.expand_dims(alpha, 0)  # 这一步的观测状态
            prior_prob = tf.matmul(prev_prob, transfer)
            prior_prob = tf.squeeze(prior_prob)  # 降维
            alpha = tf.multiply(prior_prob, tf.gather(emission, obs_status))
        self._forward_prob = tf.reduce_sum(alpha)  # 出现一个特定观测序列的概率

    @property
    def forward_prob(self):
        return self._forward_prob
