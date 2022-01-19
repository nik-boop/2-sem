


print('Шифр Цезаря')
s = "Privet  11"

def Cenc(mes, k):
    return [chr((ord(i) + k) % 65536)for i in mes]

def Cdec(mes, k):
    return [chr((65536 + (ord(i) - k) % 65536) % 65536) for i in mes]

a = Cenc(s, 10)
b = Cdec(a, 10)
print(s, a, "".join(b))


print('Взлом шифра цезаря')
def Chahack(mes):
    numdict = {}
    for i in set(mes):
        numdict[i] = mes.count(i)
    chmax= max(numdict.values())
    plist = []
    for k, v in numdict.items():
        if v == chmax:
            plist.append(k)
    for ch in plist:
        yield [chr((65536 + (ord(i) - (ord(ch) - ord(" ")) % 65536)) % 65536) for i in mes]
print(*[''.join(i) for i in list(Chahack(a))],sep="\n")

def Venc(k,m):
    k = k * (len(m) // len(k)) + k[:len(m) % len(k)]
    return list(map(lambda x: x[0]^x[1], zip([ord(i) for i in m], [ord(i) for i in k])))

def Vdec(k,c):
    k = k * (len(m) // len(k)) + k[:len(m) % len(k)]
    return ''.join([chr(i) for i in map(lambda x: x[0]^x[1], zip(c, [ord(i) for i in k]))])


print('Шифр Вижинера')
m = "1234567890"
k = "abc"
c = Venc(k, m)
print(Vdec(k, c))
