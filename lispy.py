# 2024-06-11  lispy.py

"""
居然已经是两年前的代码了。总之，下边是当时参考的文章：
- [（如何（用Python）写一个（Lisp）解释器（上）） - 悲路的文章 - 知乎](https://zhuanlan.zhihu.com/p/28989326)
- [（如何（用Python）写一个（Lisp）解释器（下）） - 悲路的文章 - 知乎](https://zhuanlan.zhihu.com/p/29186794)
- [(How to Write a (Lisp) Interpreter (in Python))](https://www.norvig.com/lispy.html)
"""

import operator as op
from typing import Callable
import math
import cmath
from fractions import Fraction
from typing import Any
import re



Number = (int, float, Fraction, complex)
Symbol = str
List   = list


######## 在 Python 里也要用的 Scheme 函数

def is_scheme_true(x: Any) -> bool:
    return not is_scheme_false(x)


def is_scheme_false(x: Any) -> bool:
    return isinstance(x, bool) and x == False


######## 语法解析

def atom(token: str):
    '''解析字面量'''
    try:
        return int(token, base=0)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            try:
                return Fraction(token)
            except ValueError:
                try:
                    return complex(token)
                except ValueError:
                    return Symbol(token)


def to_tokens(code: str) -> list[str]:
    '''将字符串转换成由token组成的列表。'''
    # 不要加入大于、小于号
    code = re.sub(r'[\(\[\{（「［【〔﹝⸨｟《]', ' ( ', code)
    code = re.sub(r'[\)\]\}）」］】〕﹞⸩｠》]', ' ) ', code)
    return code.split()


def to_forest(tokens: list[str]):
    '''从一串 token 之中读取出森林（许多棵树）'''
    '''原版实现对于 m 个 token 调用了 m 次 tokens.pop(0)，那是平方时间算法。。。所以改成了如下实现。'''
    N = len(tokens)
    index = 0

    def rec():
        nonlocal index
        if index == N:
            raise SyntaxError('unexpected EOF while reading')
        token = tokens[index]
        index += 1
        if token == ')':
            raise SyntaxError('unexpected ")"')
        elif token == '(':
            ls = []
            while tokens[index] != ')':
                ls.append(rec())
            index += 1
            return ls
        else:
            return atom(token)

    forest = []
    while index != N:
        tree = rec()
        forest.append(tree)
    return forest



def parse(program: str) -> list:
    return to_forest(to_tokens(program))




######## 环境



class Env(dict):
    '''环境是形式为 {'变量名': 值} 的字典，加上一个指向外层环境的引用。'''
    def __init__(self: "Env", parms=(), args=(), outer=None):
        self.update(zip(parms, args))
        self.outer = outer
    def copy(self: "Env"):
        '''复制自己（深拷贝）'''
        that_one = Env()
        # 使用父类 dict 的 .copy() 方法
        that_one.update(super().copy())
        # 递归地复制外部环境
        if self.outer != None:
            that_one.outer = self.outer.copy()
        return that_one
    def find(self: "Env", var: str):
        '''寻找变量出现的最内层环境。'''
        if var in self:
            return self
        elif self.outer == None:
            raise NameError("variable not found", var)
        else:
            # 递归地在复制外部环境中查找变量
            return self.outer.find(var)



######## s_eval


# 为避免和 Python 内置函数 eval() 弄混，这里叫它 s_eval
def s_eval(x, env: Env) -> Any:
    '''在某环境中对一个表达式进行求值。'''
    if isinstance(x, Symbol):      # 变量引用
        return env.find(x)[x]
    elif not isinstance(x, List):  # 字面量（？
        return x
    head = x[0]
    if head == 'quote':
        (_, exp) = x
        return exp
    elif head == 'if':
        (_, test, conseq, alt) = x
        exp = (conseq if is_scheme_true(s_eval(test, env)) else alt)
        return s_eval(exp, env)
    elif head == 'define':
        if isinstance(x[1], Symbol):
            # 变量定义
            (_, var, exp) = x
            res = s_eval(exp, env)
            env[var] = res
            return res
        elif isinstance(x[1], List):
            # 过程定义
            (_, (procname, *parms), *body) = x
            res = Procedure(parms, body, env)
            env[procname] = res
            return res
        else:
            raise SyntaxError("Unrecognized object after the 'define' in definition")
    elif head == 'set!':
        (_, var, exp) = x
        res = s_eval(exp, env)
        env.find(var)[var] = res
        return res
    elif head == 'lambda':
        (_, parms, *body) = x
        return Procedure(parms, body, env)
    elif head == 'and':
        (_, *exps) = x
        if len(exps) == 0:
            return True
        else:
            for i in range(len(exps) - 1):
                if is_scheme_false(r := s_eval(exps[i], env)):
                    return r
            return s_eval(exps[-1], env)
    elif head == 'or':
        (_, *exps) = x
        if len(exps) == 0:
            return False
        else:
            for i in range(len(exps) - 1):
                if is_scheme_true(r := s_eval(exps[i], env)):
                    return r
            return s_eval(exps[-1], env)
    elif head == 'begin':
        (_, *exps) = x
        return recorded_s_eval_sequence(exps, env)
    elif head == 'cond':
        (_, *(pred_exps_pairs)) = x
        for pred, *exps in pred_exps_pairs:
            if is_scheme_true(s_eval(pred, env)):
                return recorded_s_eval_sequence(exps, env)
        return None
    elif head == 'let':
        # let -> (lambda)
        (_, var_exp_pairs, *body) = x
        return s_eval( [ [ 'lambda', [var for var, exp in var_exp_pairs], *body], *[exp for var, exp in var_exp_pairs] ],
                      env)
    else:
        # 过程调用
        proc = s_eval(x[0], env)
        args = [ s_eval(arg, env) for arg in x[1:] ]
        return proc(*args)



def recorded_s_eval(x, env: Env) -> Any:
    '''s_eval，但把结果存进环境中名为 '_' 的变量里'''
    res = s_eval(x, env)
    env['_'] = res
    return res


def recorded_s_eval_sequence(exps: list, env: Env) -> Any:
    r = None
    for exp in exps:
        r = recorded_s_eval(exp, env)
    return r


def schemestr(exp: Any) -> str:
    '''将一个Python对象转换回可以被Scheme读取的字符串。'''
    if isinstance(exp, list):
        return '(' + ' '.join([ schemestr(element) for element in exp] ) + ')'
    else:
        return str(exp)


######## 过程

class Procedure(object):
    '''用户定义的Scheme过程。'''
    def __init__(self, parms, body, env):
        self.parms, self.body, self.env = parms, body, env
    def __call__(self, *args):
        return recorded_s_eval_sequence(self.body, Env(self.parms, args, self.env))


######## 搭建标准环境

def real_complex_generic(r_func: Callable, c_func: Callable) -> Callable:
    '''
    接收一个一元实变函数和一个一元复变函数，
    返回一个函数，该函数根据参数类型选择使用实变的还是复变的。
    '''
    return lambda num: c_func(num) if isinstance(num, complex) else r_func(num)


def set_element(ls: list[Any], index: int, val: Any) -> Any:
    ls[index] = val
    return val


def compose(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    rev_tpl = tuple(reversed(funcs))
    def res_func(x: Any) -> Any:
        for f in rev_tpl:
            x = f(x)
        return x
    return res_func


def func_iter(f: Callable[[Any], Any], times: int) -> Callable[[Any], Any]:
    def res_func(x: Any) -> Any:
        for i in range(times):
            x = f(x)
        return x
    return res_func


std_objs = {
# Lisp 语言
    'True':         True,
    'False':        False,
    'true?':        is_scheme_true,
    'false?':       is_scheme_false,
    'bool?':        lambda obj: isinstance(obj, bool),
    'apply':        lambda f, lsvar: f(*lsvar),
    'eq?':          op.is_,
    'equal?':       op.eq,
    'not':          op.not_,
    'number?':      lambda x: isinstance(x, Number),
    'procedure?':   callable,
    'symbol?':      lambda x: isinstance(x, Symbol),
    # 注意：和 C、C++ 等语言不同，在 Python 3 中，函数参数必定从左向右求值，所以（原来的解释器）可以这样去实现 begin 了：
    # lambda *x: x[-1]
    # 见 https://docs.python.org/zh-cn/3/reference/expressions.html 中的 “6.16. 求值顺序”。
    # 但为了让变量 '_' begin 的子句之间起作用，现在 begin 做成一个特殊形式，在 s_eval 里实现。
# 表操作
    'list':            lambda *x: List(x),
    'ref':             lambda ls, index: ls[index],
    'set-element!':    set_element,
    'list?':           lambda x: isinstance(x, List),
    'append-ls':       op.add,
    'append-element!': lambda ls, e: ls.append(e),
    'len':             len,
    'map-sicp':        lambda f, ls: List( f(element) for element in ls ),
    'map-ieee':        lambda f, *ls_ls: List( f(*args) for args in zip(*ls_ls) ),
    'zip':             lambda *ls_s: List(zip(*ls_s)),
# 函数什么的
    'compose':         compose,
    'func-iter':       func_iter,
# 基础算术，运算符，比较
    '+':   lambda *ls: sum(ls),
    'sum': sum,
    '-':   lambda *ls: ls[0] - ls[1] if len(ls) == 2 else -ls[0],
    '*':   lambda *ls: math.prod(ls),
    'prod': math.prod,
    '/':   op.truediv,
    '%':   op.mod,
    '//':  op.floordiv,
    '**':  op.pow,
    '<':   op.lt,
    '<=':  op.le,
    '=':   op.eq,
    '!=':  op.ne,
    '>=':  op.ge,
    '>':   op.gt,
    '&':   op.and_,
    '~':   op.inv,
    '|':   op.or_,
    '^':   op.xor,
    '<<':  op.lshift,
    '>>':  op.rshift,
    'abs': abs,
    'sq':  lambda x: x*x,
    'cb':  lambda x: x*x*x,
    'max': max,
    'min': min,
    'round': round,
    'divmod': lambda x, y: List(divmod(x, y)),
# 数学常量和浮点常量，数值来自 Wolfram Alpha
    'e':             math.e,
    'pi':            math.pi,
    'tau':           math.tau,
    'inf':           math.inf,
    'nan':           math.nan,
    'infj':          cmath.infj,
    'nanj':          cmath.nanj,
    'gamma-const':   0.5772156649015328606065120900824024310421593359399235988057672348,
    'omega-const':   0.5671432904097838729999686622103555497538157871865125081351310792,
    'catalan-const': 0.9159655941772190150546035149323841107741493742816721342664981196,
# 复数
    'complex':  complex,
    're':    lambda x: x.real if isinstance(x, complex) else x,
    'im':    lambda x: x.imag if isinstance(x, complex) else 0,
    'arg':   cmath.phase,
    'conj':  complex.conjugate,
    'rect':  cmath.rect,
    'polar': lambda z: List(cmath.polar(z)),
    'sqrt':  real_complex_generic(math.sqrt,  cmath.sqrt),
    'sin':   real_complex_generic(math.sin,   cmath.sin),
    'cos':   real_complex_generic(math.cos,   cmath.cos),
    'tan':   real_complex_generic(math.tan,   cmath.tan),
    'asin':  real_complex_generic(math.asin,  cmath.asin),
    'acos':  real_complex_generic(math.acos,  cmath.acos),
    'atan':  real_complex_generic(math.atan,  cmath.atan),
    'sinh':  real_complex_generic(math.sinh,  cmath.sinh),
    'cosh':  real_complex_generic(math.cosh,  cmath.cosh),
    'tanh':  real_complex_generic(math.tanh,  cmath.tanh),
    'asinh': real_complex_generic(math.asinh, cmath.asinh),
    'atanh': real_complex_generic(math.atanh, cmath.atanh),
    'acosh': real_complex_generic(math.acosh, cmath.acosh),
    'exp':   real_complex_generic(math.exp,   cmath.exp),
    'log':   real_complex_generic(math.log,   cmath.log),
    'log10': real_complex_generic(math.log10, cmath.log10),
    'isinf': real_complex_generic(math.isinf, cmath.isinf),
    'isnan': real_complex_generic(math.isnan, cmath.isnan),
    'isfinite': real_complex_generic(math.isfinite, cmath.isfinite),
    'isclose':  lambda a, b, max_rel_tol, min_abs_tol: cmath.isclose(a, b, rel_tol=max_rel_tol, abs_tol=min_abs_tol),
#  浮点算术和控制
    'fmod':       lambda a, b: math.fmod(a, b),
    'nextafter':  lambda x, dest: math.nextafter(x, dest),
    'frexp':      lambda a: List(math.frexp(a)),
    'ldexp':      math.ldexp,
    'ceil':       math.ceil,
    'floor':      math.floor,
    'fabs':       math.fabs,
    'copysign':   math.copysign,
    'trunc':      math.trunc,
    'ulp':        math.ulp,
    'remainder':  math.remainder,
    'modf':       lambda x: List(math.modf(x)),
    'comb':       math.comb,
    'perm':       math.perm,
    'lcm':        math.lcm,
    'gcd':        math.gcd,
    'isqrt':      math.isqrt,
    'factorial':  math.factorial,
    'fsum':       math.fsum,
    'pow-math':   math.pow,
    'pow-py-bin': lambda a, b: pow(a, b),
    'pow-py-ter': lambda a, b, c: pow(a, b, c),
    'hypot':      math.hypot,
    'expm1':      math.expm1,
    'degrees':    math.degrees,
    'radians':    math.radians,
    'atan2':      math.atan2,
    'dist':       math.dist,
    'log2':       math.log2,
    'log1p':      math.log1p,
    'gamma':      math.gamma,
    'lgamma':     math.lgamma,
    'erf':        math.erf,
    'erfc':       math.erfc,
# 分数算术
    'frac':      Fraction,
    'numer':     lambda q: q.numerator,
    'denom':     lambda q: q.denominator,
    'lim-denom': Fraction.limit_denominator,
    'tpl':       lambda q: List(Fraction.as_integer_ratio(q)),
}

std_env = Env()
std_env.update(std_objs)






######## 对外接口

std_env_varnames = list(std_objs.keys())
keywords = ['quote', 'if', 'define', 'set!', 'lambda', 'and', 'or', 'begin', 'cond', 'let']

class Interpreter(object):
    def __init__(self: "Interpreter"):
        self.g_env = std_env.copy()
    def reset(self: "Interpreter") -> None:
        self.g_env = std_env.copy()
    def run(self: "Interpreter", program: str) -> Any:
        '''
        参数是 Scheme 代码字符串（可以是多个表达式）。
        依次求出各个表达式的结果并返回（字符串格式），存储在 Python list 中。
        '''
        forest = parse(program)
        eval_res_ls = [ schemestr(recorded_s_eval(tree, self.g_env)) for tree in forest ]
        return eval_res_ls


######## 测试

if __name__ == '__main__':
    preter1 = Interpreter()
    print(preter1.run("(define x 10)"))
    print(preter1.run("(+ x 1)"))
    preter2 = Interpreter()
    print(preter2.run("(define x 20)"))
    print(preter2.run("(+ x 1)"))
    print(preter1.run("(+ x 1)"))

    print(preter1.run("(define sqrt 233)"))
    print(preter1.run("sqrt"))
    print(preter2.run("(/ (- (sqrt 5) 1) 2)"))
    print(preter2.run('''
((lambda (n)
    ((lambda (fact)
        (fact fact n))
    (lambda (ft k)
        (if (= k 1)
            1
            (* k (ft ft (- k 1))))))) 10)
'''))
    print(preter2.run('''(+ (let ((x 3)
                            (y 1))
                           (+ y (* x 10)))
                      x)'''))
    print(preter2.run('''(map-ieee +
                                   (list 1 2 3)
                                   (list 40 50 60)
                                   (list 700 800 900))'''))
    print(preter2.run("(+ 1 3) (- 1 2)"))

# TODO
# 2024-07-09:
#   Done apply
#   Done &&, ||
#   Done lin-map, ieee-map
#   Done pol, rec
#   Done math
#        将 eval 加入所模拟的 scheme 中并测试？
#   Done 能够给出 std_env; std_env_vars; 关键字;
#        标准库中其他的数学库
#        第三方数学库？
# 2024-07-10
#   Done 优化一下有关 _ 的机制，比如在 begin 中
#   Done 弃用 car cdr，只用 list
#   No   为不同用户维护不同的环境
#   Done 增加一个绘制函数图象的功能：复变函数的定义域着色
#        将更多第三方库的功能加进来
#        上线 Bot？
#        define-syntax（宏）
#        读入器宏字符， ' 和 . 以及 ,
#        let*, letrec, 命名的 let
# 2024-07-12
#        列表切片
# 2024-07-12
#        函数迭代，函数复合
# 2024-08-31
#   Done 处理 number? 函数
#   Done 把老 lispy 中该搬的东西搬过来


