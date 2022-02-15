import openfermion
import numpy as np
import copy as cp
import re
import scipy

from openfermion import *



class OperatorPool:
    def __init__(self):
        self.n_orb = 0
        self.n_occ_a = 0
        self.n_occ_b = 0
        self.n_vir_a = 0
        self.n_vir_b = 0

        self.n_spin_orb = 0
        self.gradient_print_thresh = 0

    def init(self,n_orb,
            n_occ_a=None,
            n_occ_b=None,
            n_vir_a=None,
            n_vir_b=None):
        self.n_orb = n_orb
        self.n_spin_orb = 2*self.n_orb

        if n_occ_a!=None and n_occ_b!=None:
            assert(n_occ_a == n_occ_b)
            self.n_occ = n_occ_a
            self.n_occ_a = n_occ_a
            self.n_occ_b = n_occ_b
            self.n_vir = n_vir_a
            self.n_vir_a = n_vir_a
            self.n_vir_b = n_vir_b
        self.n_ops = 0

        self.generate_SQ_Operators()

    def generate_SQ_Operators(self):
        print("Virtual: Reimplement")
        exit()

    def generate_SparseMatrix(self):
        self.spmat_ops = []
        print(" Generate Sparse Matrices for operators in pool")
        for op in self.fermi_ops:
            self.spmat_ops.append(transforms.get_sparse_operator(op, n_qubits = self.n_spin_orb))
        assert(len(self.spmat_ops) == self.n_ops)
        return

    def get_string_for_term(self,op):

        opstring = ""
        opstring_pauli = ""
        spins = ""
        for t in op.terms:

            opstring = "("
            if t[0][1] == 'X' or t[0][1] == 'Y' or t[0][1] == 'Z':
                if np.imag(op.terms[t]) > 0:
                    opstring_pauli += " + "+str(op.terms[t])+" "
                if np.imag(op.terms[t]) < 0:
                    opstring_pauli += " - "+str(abs(op.terms[t]))+"j "
            for ti in t:
                opstring += str(int(ti[0]/2))
                if ti[1] == 0:
                    opstring += "  "
                elif ti[1] == 1:
                    opstring += "' "
                elif ti[1] == 'X' or ti[1] == 'Y' or ti[1] == 'Z':
                    if np.imag(op.terms[t]) != 0:
                        opstring_pauli += ti[1]+str(int(ti[0]))
                else:
                    print("wrong")
                    exit()
                spins += str(ti[0]%2)
                if ti[1] == 'X' or ti[1] == 'Y' or ti[1] == 'Z':
                    spins = " "

#            if self.fermi_ops[i].terms[t] > 0:
#                spins = "+"+spins
#            if self.fermi_ops[i].terms[t] < 0:
#                spins = "-"+spins
            opstring += ")"
            spins += " "
        opstring = " %18s : %s" %(opstring, spins)
        if ti[1] == 'X' or ti[1] == 'Y' or ti[1] == 'Z':
            opstring = opstring_pauli
        return opstring



    def compute_gradient_i(self,i,v,sig):
        """
        For a previously optimized state |n>, compute the gradient g(k) of exp(c(k) A(k))|n>
        g(k) = 2Real<HA(k)>

        Note - this assumes A(k) is an antihermitian operator. If this is not the case, the derived class should
        reimplement this function. Of course, also assumes H is hermitian

        v   = current_state
        sig = H*v

        """
        opA = self.spmat_ops[i]
        gi = 2*(sig.transpose().conj().dot(opA.dot(v)))
        assert(gi.shape == (1,1))
        gi = gi[0,0]
        assert(np.isclose(gi.imag,0))
        gi = gi.real

        opstring = self.get_string_for_term(self.fermi_ops[i])

        if abs(gi) > self.gradient_print_thresh:
            print(" %4i %12.8f %s" %(i, gi, opstring) )

        return gi


class spin_complement_GSD(OperatorPool):
# {{{
    def generate_SQ_Operators(self):
        alpha_orbs = [2*i for i in range(self.n_orb)]
        beta_orbs = [2*i+1 for i in range(self.n_orb)]

        ops = []
        #aa
        for p in alpha_orbs:
            for q in alpha_orbs:
                if p>=q:
                    continue
                #if abs(hamiltonian_op.one_body_tensor[p,q]) < 1e-8:
                #    print(" Dropping term %4i %4i" %(p,q), " V= %+6.1e" %hamiltonian_op.one_body_tensor[p,q])
                #    continue
                one_elec = openfermion.FermionOperator(((q,1),(p,0)))-openfermion.FermionOperator(((p,1),(q,0)))
                one_elec += openfermion.FermionOperator(((q+1,1),(p+1,0)))-openfermion.FermionOperator(((p+1,1),(q+1,0)))
                ops.append(one_elec)
        #aa
        pq = 0
        for p in alpha_orbs:
            for q in alpha_orbs:
                if p>q:
                    continue
                rs = 0
                for r in alpha_orbs:
                    for s in alpha_orbs:
                        if r>s:
                            continue
                        if pq<rs:
                            continue
                        #if abs(hamiltonian_op.two_body_tensor[p,r,s,q]) < 1e-8:
                            #print(" Dropping term %4i %4i %4i %4i" %(p,r,s,q), " V= %+6.1e" %hamiltonian_op.two_body_tensor[p,r,s,q])
                            #continue
                        two_elec = openfermion.FermionOperator(((r,1),(p,0),(s,1),(q,0)))-openfermion.FermionOperator(((q,1),(s,0),(p,1),(r,0)))
                        two_elec += openfermion.FermionOperator(((r+1,1),(p+1,0),(s+1,1),(q+1,0)))-openfermion.FermionOperator(((q+1,1),(s+1,0),(p+1,1),(r+1,0)))
                        ops.append(two_elec)
                        rs += 1
                pq += 1


        #ab
        pq = 0
        for p in alpha_orbs:
            for q in beta_orbs:
                rs = 0
                for r in alpha_orbs:
                    for s in beta_orbs:
                        if pq<rs:
                            continue
                        two_elec = openfermion.FermionOperator(((r,1),(p,0),(s,1),(q,0)))-openfermion.FermionOperator(((q,1),(s,0),(p,1),(r,0)))
                        if p>q:
                            continue
                        two_elec += openfermion.FermionOperator(((s-1,1),(q-1,0),(r+1,1),(p+1,0)))-openfermion.FermionOperator(((p+1,1),(r+1,0),(q-1,1),(s-1,0)))
                        ops.append(two_elec)
                        rs += 1
                pq += 1

        self.fermi_ops = ops
        self.n_ops = len(self.fermi_ops)
        print(" Number of operators: ", self.n_ops)
        return
# }}}




class spin_complement_GSD2(OperatorPool):
# {{{
    def generate_SQ_Operators(self):
        """
        n_orb is number of spatial orbitals assuming that spin orbitals are labelled
        0a,0b,1a,1b,2a,2b,3a,3b,....  -> 0,1,2,3,...
        """

        print(" Form spin-complemented GSD operators")

        self.fermi_ops = []
        for p in range(0,self.n_orb):
            pa = 2*p
            pb = 2*p+1

            for q in range(p,self.n_orb):
                qa = 2*q
                qb = 2*q+1

                termA =  FermionOperator(((pa,1),(qa,0)))
                termA += FermionOperator(((pb,1),(qb,0)))

                termA -= hermitian_conjugated(termA)

                termA = normal_ordered(termA)

                if termA.many_body_order() > 0:
                    self.fermi_ops.append(termA)


        pq = -1
        for p in range(0,self.n_orb):
            pa = 2*p
            pb = 2*p+1

            for q in range(p,self.n_orb):
                qa = 2*q
                qb = 2*q+1

                pq += 1

                rs = -1
                for r in range(0,self.n_orb):
                    ra = 2*r
                    rb = 2*r+1

                    for s in range(r,self.n_orb):
                        sa = 2*s
                        sb = 2*s+1

                        rs += 1

                        if(pq > rs):
                            continue

                        termA =  FermionOperator(((ra,1),(pa,0),(sa,1),(qa,0)))
                        termA += FermionOperator(((rb,1),(pb,0),(sb,1),(qb,0)))

                        termB =  FermionOperator(((ra,1),(pa,0),(sb,1),(qb,0)))
                        termB += FermionOperator(((rb,1),(pb,0),(sa,1),(qa,0)))

                        termC =  FermionOperator(((ra,1),(pb,0),(sb,1),(qa,0)))
                        termC += FermionOperator(((rb,1),(pa,0),(sa,1),(qb,0)))

#                        termA =  FermionOperator(((ra,1),(pa,0),(sa,1),(qa,0)))
#                        termA += FermionOperator(((rb,1),(pb,0),(sb,1),(qb,0)))
#
#                        termB =  FermionOperator(((ra,1),(pa,0),(sb,1),(qb,0)))
#                        termB += FermionOperator(((rb,1),(pb,0),(sa,1),(qa,0)))
#
#                        termC =  FermionOperator(((ra,1),(pb,0),(sb,1),(qa,0)))
#                        termC += FermionOperator(((rb,1),(pa,0),(sa,1),(qb,0)))

#                        print()
#                        print(p,q,r,s)
#                        print(termA)
#                        print(termB)
#                        print(termC)
                        termA -= hermitian_conjugated(termA)
                        termB -= hermitian_conjugated(termB)
                        termC -= hermitian_conjugated(termC)

                        termA = normal_ordered(termA)
                        termB = normal_ordered(termB)
                        termC = normal_ordered(termC)

                        if termA.many_body_order() > 0:
                            self.fermi_ops.append(termA)

                        if termB.many_body_order() > 0:
                            self.fermi_ops.append(termB)

                        if termC.many_body_order() > 0:
                            self.fermi_ops.append(termC)

        self.n_ops = len(self.fermi_ops)
        print(" Number of operators: ", self.n_ops)
        return
# }}}




class singlet_GSD(OperatorPool):
# {{{
    def generate_SQ_Operators(self):
        """
        n_orb is number of spatial orbitals assuming that spin orbitals are labelled
        0a,0b,1a,1b,2a,2b,3a,3b,....  -> 0,1,2,3,...
        """

        print(" Form singlet GSD operators")

        self.fermi_ops = []
        for p in range(0,self.n_orb):
            pa = 2*p
            pb = 2*p+1

            for q in range(p,self.n_orb):
                qa = 2*q
                qb = 2*q+1

                termA =  FermionOperator(((pa,1),(qa,0)))
                termA += FermionOperator(((pb,1),(qb,0)))

                termA -= hermitian_conjugated(termA)

                termA = normal_ordered(termA)

                #Normalize
                coeffA = 0
                for t in termA.terms:
                    coeff_t = termA.terms[t]
                    coeffA += coeff_t * coeff_t

                if termA.many_body_order() > 0:
                    termA = termA/np.sqrt(coeffA)
                    self.fermi_ops.append(termA)


        pq = -1
        for p in range(0,self.n_orb):
            pa = 2*p
            pb = 2*p+1

            for q in range(p,self.n_orb):
                qa = 2*q
                qb = 2*q+1

                pq += 1

                rs = -1
                for r in range(0,self.n_orb):
                    ra = 2*r
                    rb = 2*r+1

                    for s in range(r,self.n_orb):
                        sa = 2*s
                        sb = 2*s+1

                        rs += 1

                        if(pq > rs):
                            continue

#                        oplist = []
#                        oplist.append(FermionOperator(((ra,1),(pa,0),(sa,1),(qa,0)), 2/np.sqrt(12)))
#                        oplist.append(FermionOperator(((rb,1),(pb,0),(sb,1),(qb,0)), 2/np.sqrt(12)))
#                        oplist.append(FermionOperator(((ra,1),(pa,0),(sb,1),(qb,0)), 1/np.sqrt(12)))
#                        oplist.append(FermionOperator(((rb,1),(pb,0),(sa,1),(qa,0)), 1/np.sqrt(12)))
#                        oplist.append(FermionOperator(((ra,1),(pb,0),(sb,1),(qa,0)), 1/np.sqrt(12)))
#                        oplist.append(FermionOperator(((rb,1),(pa,0),(sa,1),(qb,0)), 1/np.sqrt(12)))
#
#                        print(p,q,r,s)
#                        for i in range(len(oplist)):
#                            oplist[i] -= hermitian_conjugated(oplist[i])
#                        for i in range(len(oplist)):
#                            for j in range(i+1,len(oplist)):
#                                opi = oplist[i]
#                                opj = oplist[i]
#                                opij = opi*opj - opj*opi
#                                opij = normal_ordered(opij)
#                                print(opij, end='')
#                        print()
                        termA =  FermionOperator(((ra,1),(pa,0),(sa,1),(qa,0)), 2/np.sqrt(12))
                        termA += FermionOperator(((rb,1),(pb,0),(sb,1),(qb,0)), 2/np.sqrt(12))
                        termA += FermionOperator(((ra,1),(pa,0),(sb,1),(qb,0)), 1/np.sqrt(12))
                        termA += FermionOperator(((rb,1),(pb,0),(sa,1),(qa,0)), 1/np.sqrt(12))
                        termA += FermionOperator(((ra,1),(pb,0),(sb,1),(qa,0)), 1/np.sqrt(12))
                        termA += FermionOperator(((rb,1),(pa,0),(sa,1),(qb,0)), 1/np.sqrt(12))

                        termB =  FermionOperator(((ra,1),(pa,0),(sb,1),(qb,0)),  1/2.0)
                        termB += FermionOperator(((rb,1),(pb,0),(sa,1),(qa,0)),  1/2.0)
                        termB += FermionOperator(((ra,1),(pb,0),(sb,1),(qa,0)), -1/2.0)
                        termB += FermionOperator(((rb,1),(pa,0),(sa,1),(qb,0)), -1/2.0)

                        termA -= hermitian_conjugated(termA)
                        termB -= hermitian_conjugated(termB)

                        termA = normal_ordered(termA)
                        termB = normal_ordered(termB)

                        #Normalize
                        coeffA = 0
                        coeffB = 0
                        for t in termA.terms:
                            coeff_t = termA.terms[t]
                            coeffA += coeff_t * coeff_t
                        for t in termB.terms:
                            coeff_t = termB.terms[t]
                            coeffB += coeff_t * coeff_t


                        if termA.many_body_order() > 0:
                            termA = termA/np.sqrt(coeffA)
                            self.fermi_ops.append(termA)

                        if termB.many_body_order() > 0:
                            termB = termB/np.sqrt(coeffB)
                            self.fermi_ops.append(termB)

        self.n_ops = len(self.fermi_ops)
        print(" Number of operators: ", self.n_ops)
        return
# }}}

class qubit_GSD(OperatorPool):

    def generate_SQ_Operators(self):
        """
        n_orb is number of spatial orbitals assuming that spin orbitals are labelled
        0a,0b,1a,1b,2a,2b,3a,3b,....  -> 0,1,2,3,...
        """

        print(" Form singlet GSD operators")

        self.fermi_ops = []
        for p in range(0, self.n_orb):
            pa = 2 * p
            pb = 2 * p + 1

            for q in range(p, self.n_orb):
                qa = 2 * q
                qb = 2 * q + 1

                termA = FermionOperator(((pa, 1), (qa, 0)))
                termA += FermionOperator(((pb, 1), (qb, 0)))

                termA -= hermitian_conjugated(termA)

                termA = normal_ordered(termA)

                # Normalize
                coeffA = 0
                for t in termA.terms:
                    coeff_t = termA.terms[t]
                    coeffA += coeff_t * coeff_t

                if termA.many_body_order() > 0:
                    termA = termA / np.sqrt(coeffA)
                    self.fermi_ops.append(termA)

        pq = -1
        for p in range(0, self.n_orb):
            pa = 2 * p
            pb = 2 * p + 1

            for q in range(p, self.n_orb):
                qa = 2 * q
                qb = 2 * q + 1

                pq += 1

                rs = -1
                for r in range(0, self.n_orb):
                    ra = 2 * r
                    rb = 2 * r + 1

                    for s in range(r, self.n_orb):
                        sa = 2 * s
                        sb = 2 * s + 1

                        rs += 1

                        if (pq > rs):
                            continue

                        termA = FermionOperator(((ra, 1), (pa, 0), (sa, 1), (qa, 0)), 2 / np.sqrt(12))
                        termA += FermionOperator(((rb, 1), (pb, 0), (sb, 1), (qb, 0)), 2 / np.sqrt(12))
                        termA += FermionOperator(((ra, 1), (pa, 0), (sb, 1), (qb, 0)), 1 / np.sqrt(12))
                        termA += FermionOperator(((rb, 1), (pb, 0), (sa, 1), (qa, 0)), 1 / np.sqrt(12))
                        termA += FermionOperator(((ra, 1), (pb, 0), (sb, 1), (qa, 0)), 1 / np.sqrt(12))
                        termA += FermionOperator(((rb, 1), (pa, 0), (sa, 1), (qb, 0)), 1 / np.sqrt(12))

                        termB = FermionOperator(((ra, 1), (pa, 0), (sb, 1), (qb, 0)), 1 / 2.0)
                        termB += FermionOperator(((rb, 1), (pb, 0), (sa, 1), (qa, 0)), 1 / 2.0)
                        termB += FermionOperator(((ra, 1), (pb, 0), (sb, 1), (qa, 0)), -1 / 2.0)
                        termB += FermionOperator(((rb, 1), (pa, 0), (sa, 1), (qb, 0)), -1 / 2.0)

                        termA -= hermitian_conjugated(termA)
                        termB -= hermitian_conjugated(termB)

                        termA = normal_ordered(termA)
                        termB = normal_ordered(termB)

                        # Normalize
                        coeffA = 0

                        for t in termA.terms:
                            coeff_t = termA.terms[t]
                            coeffA += coeff_t * coeff_t

                        coeffB = 0

                        for t in termB.terms:
                            coeff_t = termB.terms[t]
                            coeffB += coeff_t * coeff_t

                        if termA.many_body_order() > 0:
                            termA = termA / np.sqrt(coeffA)
                            self.fermi_ops.append(termA)

                        if termB.many_body_order() > 0:
                            termB = termB / np.sqrt(coeffB)
                            self.fermi_ops.append(termB)

        self.n_ops = len(self.fermi_ops)
        # print(" Number of fermionic operators: ", self.n_ops)

        n = self.n_spin_orb

        pool_vec = np.zeros((4 ** n,))

        for i in self.fermi_ops:
            pauli = openfermion.transforms.jordan_wigner(i)
            for line in pauli.terms:
                line = str(line)
                # print(line)
                Bin = np.zeros((2 * n,), dtype=int)
                X_pat_1 = re.compile("(\d{,2}), 'X'")
                X_1 = X_pat_1.findall(line)
                if X_1:
                    for i in X_1:
                        k = int(i)
                        Bin[n + k] = 1
                Y_pat_1 = re.compile("(\d{,2}), 'Y'")
                Y_1 = Y_pat_1.findall(line)
                if Y_1:
                    for i in Y_1:
                        k = int(i)
                        Bin[n + k] = 1
                        Bin[k] = 1
                Z_pat_1 = re.compile("(\d{,2}), 'Z'")
                Z_1 = Z_pat_1.findall(line)
                if Z_1:
                    for i in Z_1:
                        k = int(i)
                        Bin[k] = 1
                # print(Bin)
                index = int("".join(str(x) for x in Bin), 2)
                # print("index", index)

                pool_vec[index] = int(1)

        nz = np.nonzero(pool_vec)[0]

        # print("pauli pool size:", len(pool_vec[nz]))

        self.fermi_ops = []

        m = 2*n

        for i in nz:
            p = int(i)
            bi = bin(p)
            b_string = [int(j) for j in bi[2:].zfill(m)]
            pauli_string = ''
            flip = []
            for k in range(n):
                if b_string[k] == 0:
                    if b_string[k + n] == 1:
                        pauli_string += 'X%d ' % k
                        flip.append(k)
                if b_string[k] == 1:
                    if b_string[k + n] == 1:
                        pauli_string += 'Y%d ' % k
                        flip.append(k)
            flip.sort()
            z_string = list(range(flip[0] + 1,flip[1]))
            if len(flip) == 4:
                for i in range(flip[2] + 1, flip[3]):
                    z_string.append(i)
            # print("Z string:", z_string)
            for i in z_string:
                b_string[i] += 1
                b_string[i] = b_string[i] % 2
            for k in range(n):
                if b_string[k] == 1:
                    if b_string[k + n] == 0:
                        pauli_string += 'Z%d ' % k
            A = QubitOperator(pauli_string, 0 + 1j)
            # print("Pauli:", pauli_string)
            self.fermi_ops.append(A)

        self.n_ops = len(self.fermi_ops)

        print(" Number of pauli operators: ", self.n_ops)

        return #get individual pauli string from singlet GSD up down ....  # qubit pool (w/o Zs) generated from singlet_GSD

class com_gen(OperatorPool):  #brute force searching of 2n-2 minimal complete pool
    def generate_SQ_Operators(self):

        self.bin_pool = []
        self.fermi_ops = []

        ii = self.n_spin_orb        

        for i in range(2 ** (2 * ii)):
            b_string = [int(j) for j in bin(i)[2:].zfill(2 * ii)]
            self.bin_pool.append(b_string)

        self.odd_string = []

        for i in self.bin_pool:
            if sum(i[k] * i[k + ii] for k in range(ii)) % 2 == 1:
                self.odd_string.append(i)

        print("total number of antisymmetric ops :"+str(len(self.odd_string)))

        rank = 0

        while rank < 2 ** ii -1:
            random.shuffle(self.odd_string)
            first_picked = self.odd_string[:(2 * ii - 2)]
            picked = self.odd_string[:(2 * ii - 2)]
            
    
            pool_vec = np.zeros((4 ** ii,))
    
            for i in picked:
                index = int("".join(str(x) for x in i), 2)
                pool_vec[index] = 1
    
            length = 0
    
            while len(picked) < 4 ** ii:
                new = []
                if length == 0:
                    end = len(picked)
                else:
                    end = length
                for i in range(end):
                    for j in range(i+1, len(picked)):
                        Bin = [(picked[i][k] + picked[j][k]) % 2 for k in range(2 * ii)]
                        index = int("".join(str(x) for x in Bin), 2)
                        if pool_vec[index] == 0:
                            if sum(Bin[k] * Bin[k + ii] for k in range(ii)) % 2 == 1:
                                new.append(Bin)
                                pool_vec[index] = 1
                length = len(new)
                for i in new:
                    picked.insert(0, i)
                if length == 0:
                    break

            print('size of pool %12i' % (len(first_picked)))
            print('size of commutator set %12i' % (len(picked)))
    
            self.generated_ops = []
    
            for i in range(len(picked)):
                pauli_string = ''
                for j in range(ii):
                    if picked[i][j] == 0:
                        if picked[i][j + ii] == 1:
                            pauli_string += 'X%d ' % j
                    if picked[i][j] == 1:
                        if picked[i][j + ii] == 0:
                            pauli_string += 'Z%d ' % j
                        else:
                            pauli_string += 'Y%d ' % j
                A = QubitOperator(pauli_string, 0+1j)
                self.generated_ops.append(A)

            generated_pool = []
    
            for op in self.generated_ops:
                generated_pool.append(transforms.get_sparse_operator(op, n_qubits=ii))
    
            over_mat = np.zeros(shape=(len(generated_pool), len(generated_pool)))
            self.vec = np.random.rand(2 ** ii, 1)
            norm = 0
        
            for i in self.vec:
                norm += i * i
        
            self.vec = np.true_divide(self.vec, np.sqrt(norm))
            self.vec = scipy.sparse.csc_matrix(self.vec)
        
            for i in range(len(self.generated_ops)):
                # print(self.generated_ops[i])
                for j in range(len(self.generated_ops)):
                    element = self.vec.transpose().conjugate().dot(generated_pool[i].transpose().conjugate().dot(generated_pool[j].dot(self.vec)))[0, 0]
                    over_mat[i, j] = element.real
    
            rank = np.linalg.matrix_rank(over_mat, tol=1e-12)


        print("Complete set found")
        print("final cummutator set size:", len(picked))
        for i in range(len(picked)):
            pauli_string = ''
            for j in range(ii):
                if picked[i][j] == 0:
                    if picked[i][j + ii] == 1:
                        pauli_string += 'X%d ' % j
                if picked[i][j] == 1:
                    if picked[i][j + ii] == 0:
                        pauli_string += 'Z%d ' % j
                    else:
                        pauli_string += 'Y%d ' % j
            print(pauli_string)
    
        print("rank =", rank)

        for i in range(len(first_picked)):
            pauli_string = ''
            for j in range(ii):
                if first_picked[i][j] == 0:
                    if first_picked[i][j + ii] == 1:
                        pauli_string += 'X%d ' % j
                if first_picked[i][j] == 1:
                    if first_picked[i][j + ii] == 0:
                        pauli_string += 'Z%d ' % j
                    else:
                        pauli_string += 'Y%d ' % j
            A = QubitOperator(pauli_string, 0+1j)
            self.fermi_ops.append(A)

        self.n_ops = len(self.fermi_ops) 
class v(OperatorPool):   #V pool in qubit-adapt paper
    def generate_SQ_Operators(self):

        self.bin_pool = []
        self.fermi_ops = []

        ii = self.n_spin_orb        

        first_picked = []
        Y0 = np.zeros((2 * ii)).tolist()
        Y0[0] = 1
        Y0[ii] = 1
        Y0 = [int(k) for k in Y0]
        first_picked.append(Y0)

        for i in range(1, ii):
            for j in first_picked:
                j[i] = int(1)
                j = [int(k) for k in j]

            Y = np.zeros((2 * ii)).tolist()
            Y[i] = int(1)
            Y[i+ii] = int(1)
            Y = [int(k) for k in Y]
            first_picked.append(Y)

            if i > 1:
                Y = np.zeros((2 * ii)).tolist()
                Y[i-1] = int(1)
                Y[i+ii-1] = int(1)
                Y = [int(k) for k in Y]
                first_picked.append(Y)

        picked = first_picked.copy()

        for i in range(len(picked)):
            pauli_string = ''
            for j in range(ii):
                if picked[i][j] == 0:
                    if picked[i][j + ii] == 1:
                        pauli_string += 'X%d ' % j
                if picked[i][j] == 1:
                    if picked[i][j + ii] == 0:
                        pauli_string += 'Z%d ' % j
                    else:
                        pauli_string += 'Y%d ' % j
            # print(pauli_string)

        for i in range(len(first_picked)):
            pauli_string = ''
            for j in range(ii):
                if first_picked[i][j] == 0:
                    if first_picked[i][j + ii] == 1:
                        pauli_string += 'X%d ' % j
                if first_picked[i][j] == 1:
                    if first_picked[i][j + ii] == 0:
                        pauli_string += 'Z%d ' % j
                    else:
                        pauli_string += 'Y%d ' % j
            A = QubitOperator(pauli_string, 0+1j)
            self.fermi_ops.append(A)
    
        self.n_ops = len(self.fermi_ops) 
class g(OperatorPool): #G pool in qubit-adapt paper
    def generate_SQ_Operators(self):

        self.bin_pool = []
        self.fermi_ops = []

        ii = self.n_spin_orb        

        first_picked = []

        for i in range(ii-1):
            ZY = np.zeros((2 * ii)).tolist()
            ZY[i] = int(1)

            ZY[i+1] = int(1)
            ZY[i+ii+1] = int(1)

            ZY = [int(k) for k in ZY]
            first_picked.append(ZY)

            Y = np.zeros((2 * ii)).tolist()
            Y[i] = int(1)
            Y[i+ii] = int(1)
            Y = [int(k) for k in Y]
            first_picked.append(Y)

        picked = first_picked.copy()

        for i in range(len(picked)):
            pauli_string = ''
            for j in range(ii):
                if picked[i][j] == 0:
                    if picked[i][j + ii] == 1:
                        pauli_string += 'X%d ' % j
                if picked[i][j] == 1:
                    if picked[i][j + ii] == 0:
                        pauli_string += 'Z%d ' % j
                    else:
                        pauli_string += 'Y%d ' % j
            # print(pauli_string)

        for i in range(len(first_picked)):
            pauli_string = ''
            for j in range(ii):
                if first_picked[i][j] == 0:
                    if first_picked[i][j + ii] == 1:
                        pauli_string += 'X%d ' % j
                if first_picked[i][j] == 1:
                    if first_picked[i][j + ii] == 0:
                        pauli_string += 'Z%d ' % j
                    else:
                        pauli_string += 'Y%d ' % j
            A = QubitOperator(pauli_string, 0+1j)
            self.fermi_ops.append(A)
    
        self.n_ops = len(self.fermi_ops) 
class QE(OperatorPool): #qubit-excitation pool

    def generate_SQ_Operators(self):
        """
        n_orb is number of spatial orbitals assuming that spin orbitals are labelled
        0a,0b,1a,1b,2a,2b,3a,3b,....  -> 0,1,2,3,...
        """
        
        print(" Form singlet GSD operators")
        
        self.fermi = []
        for p in range(0,self.n_orb):
            pa = 2*p
            pb = 2*p+1
 
            for q in range(p,self.n_orb):
                qa = 2*q
                qb = 2*q+1
        
                termA =  FermionOperator(((pa,1),(qa,0)))
                termA -= hermitian_conjugated(termA)
                termA = normal_ordered(termA)
                if termA.many_body_order() > 0:
                    self.fermi.append(termA)

                termA = FermionOperator(((pb,1),(qb,0)))
                termA -= hermitian_conjugated(termA)               
                termA = normal_ordered(termA)
                if termA.many_body_order() > 0:
                    self.fermi.append(termA)                      
      
        pq = -1 
        for p in range(0,self.n_orb):
            pa = 2*p
            pb = 2*p+1
 
            for q in range(p,self.n_orb):
                qa = 2*q
                qb = 2*q+1
        
                pq += 1
        
                rs = -1 
                for r in range(0,self.n_orb):
                    ra = 2*r
                    rb = 2*r+1
                    
                    for s in range(r,self.n_orb):
                        sa = 2*s
                        sb = 2*s+1
                    
                        rs += 1
                    
                        if(pq > rs):
                            continue

                        termA =  FermionOperator(((ra,1),(pa,0),(sa,1),(qa,0)))
                        termA -= hermitian_conjugated(termA)
                        termA = normal_ordered(termA)
                        if termA.many_body_order() > 0:
                            self.fermi.append(termA)

                        termA = FermionOperator(((rb,1),(pb,0),(sb,1),(qb,0)))
                        termA -= hermitian_conjugated(termA)
                        termA = normal_ordered(termA)
                        if termA.many_body_order() > 0:
                            self.fermi.append(termA)

                        termA = FermionOperator(((ra,1),(pa,0),(sb,1),(qb,0)))
                        termA -= hermitian_conjugated(termA)
                        termA = normal_ordered(termA)
                        if termA.many_body_order() > 0:
                            self.fermi.append(termA)

                        termA = FermionOperator(((rb,1),(pb,0),(sa,1),(qa,0)))
                        termA -= hermitian_conjugated(termA)
                        termA = normal_ordered(termA)
                        if termA.many_body_order() > 0:
                            self.fermi.append(termA)

                        termA = FermionOperator(((ra,1),(pb,0),(sb,1),(qa,0)))
                        termA -= hermitian_conjugated(termA)
                        termA = normal_ordered(termA)
                        if termA.many_body_order() > 0:
                            self.fermi.append(termA)

                        termA = FermionOperator(((rb,1),(pa,0),(sa,1),(qb,0)))
                        termA -= hermitian_conjugated(termA)
                        termA = normal_ordered(termA)
                        if termA.many_body_order() > 0:
                            self.fermi.append(termA)

        self.n_ops = len(self.fermi)

        n = self.n_spin_orb

        pool_vec = np.zeros((4 ** n,))

        self.fermi_ops = []

        for i in self.fermi:
            pauli = openfermion.transforms.jordan_wigner(i)
            op = QubitOperator('X0', 0)
            for line in pauli.terms:
                coeff = pauli.terms[line]
                line = str(line)
                # print(line)
                Bin = np.zeros((2 * n,), dtype=int)
                X_pat_1 = re.compile("(\d{,2}), 'X'")
                X_1 = X_pat_1.findall(line)
                if X_1:
                    for i in X_1:
                        k = int(i)
                        Bin[n + k] = 1
                Y_pat_1 = re.compile("(\d{,2}), 'Y'")
                Y_1 = Y_pat_1.findall(line)
                if Y_1:
                    for i in Y_1:
                        k = int(i)
                        Bin[n + k] = 1
                        Bin[k] = 1
                Z_pat_1 = re.compile("(\d{,2}), 'Z'")
                Z_1 = Z_pat_1.findall(line)
                if Z_1:
                    for i in Z_1:
                        k = int(i)
                        Bin[k] = 1
                # print(Bin)
                index = int("".join(str(x) for x in Bin), 2)
                # print("index", index)

                pool_vec[index] = int(1)

                pauli_string = ''
                flip = []
                for k in range(n):
                    if Bin[k] == 0:
                        if Bin[k + n] == 1:
                            pauli_string += 'X%d ' % k
                            flip.append(k)
                    if Bin[k] == 1:
                        if Bin[k + n] == 1:
                            pauli_string += 'Y%d ' % k
                            flip.append(k)
                flip.sort()
                z_string = list(range(flip[0] + 1,flip[1]))
                if len(flip) == 4:
                    for i in range(flip[2] + 1, flip[3]):
                        z_string.append(i)
                # print("Z string:", z_string)
                for i in z_string:
                    Bin[i] += 1
                    Bin[i] = Bin[i] % 2
                for k in range(n):
                    if Bin[k] == 1:
                        if Bin[k + n] == 0:
                            pauli_string += 'Z%d ' % k
                A = QubitOperator(pauli_string, coeff)
                op += A

            # print(op)
            self.fermi_ops.append(op)

        self.n_ops = len(self.fermi_ops)
        print(" Number of qubit excitation operators: ", self.n_ops)
        return

class singlet_SD(OperatorPool):
# {{{
    def generate_SQ_Operators(self):
        """
        0a,0b,1a,1b,2a,2b,3a,3b,....  -> 0,1,2,3,...
        """

        print(" Form singlet SD operators")
        self.fermi_ops = []

        assert(self.n_occ_a == self.n_occ_b)
        n_occ = self.n_occ
        n_vir = self.n_vir

        for i in range(0,n_occ):
            ia = 2*i
            ib = 2*i+1

            for a in range(0,n_vir):
                aa = 2*n_occ + 2*a
                ab = 2*n_occ + 2*a+1

                termA =  FermionOperator(((aa,1),(ia,0)), 1/np.sqrt(2))
                termA += FermionOperator(((ab,1),(ib,0)), 1/np.sqrt(2))

                termA -= hermitian_conjugated(termA)

                termA = normal_ordered(termA)

                #Normalize
                coeffA = 0
                for t in termA.terms:
                    coeff_t = termA.terms[t]
                    coeffA += coeff_t * coeff_t

                if termA.many_body_order() > 0:
                    termA = termA/np.sqrt(coeffA)
                    self.fermi_ops.append(termA)


        for i in range(0,n_occ):
            ia = 2*i
            ib = 2*i+1

            for j in range(i,n_occ):
                ja = 2*j
                jb = 2*j+1

                for a in range(0,n_vir):
                    aa = 2*n_occ + 2*a
                    ab = 2*n_occ + 2*a+1

                    for b in range(a,n_vir):
                        ba = 2*n_occ + 2*b
                        bb = 2*n_occ + 2*b+1

                        termA =  FermionOperator(((aa,1),(ba,1),(ia,0),(ja,0)), 2/np.sqrt(12))
                        termA += FermionOperator(((ab,1),(bb,1),(ib,0),(jb,0)), 2/np.sqrt(12))
                        termA += FermionOperator(((aa,1),(bb,1),(ia,0),(jb,0)), 1/np.sqrt(12))
                        termA += FermionOperator(((ab,1),(ba,1),(ib,0),(ja,0)), 1/np.sqrt(12))
                        termA += FermionOperator(((aa,1),(bb,1),(ib,0),(ja,0)), 1/np.sqrt(12))
                        termA += FermionOperator(((ab,1),(ba,1),(ia,0),(jb,0)), 1/np.sqrt(12))

                        termB  = FermionOperator(((aa,1),(bb,1),(ia,0),(jb,0)), 1/2)
                        termB += FermionOperator(((ab,1),(ba,1),(ib,0),(ja,0)), 1/2)
                        termB += FermionOperator(((aa,1),(bb,1),(ib,0),(ja,0)), -1/2)
                        termB += FermionOperator(((ab,1),(ba,1),(ia,0),(jb,0)), -1/2)

                        termA -= hermitian_conjugated(termA)
                        termB -= hermitian_conjugated(termB)

                        termA = normal_ordered(termA)
                        termB = normal_ordered(termB)

                        #Normalize
                        coeffA = 0
                        coeffB = 0
                        for t in termA.terms:
                            coeff_t = termA.terms[t]
                            coeffA += coeff_t * coeff_t
                        for t in termB.terms:
                            coeff_t = termB.terms[t]
                            coeffB += coeff_t * coeff_t


                        if termA.many_body_order() > 0:
                            termA = termA/np.sqrt(coeffA)
                            self.fermi_ops.append(termA)

                        if termB.many_body_order() > 0:
                            termB = termB/np.sqrt(coeffB)
                            self.fermi_ops.append(termB)

        self.n_ops = len(self.fermi_ops)
        print(" Number of operators: ", self.n_ops)
        return
    # }}}



def unrestricted_SD(n_occ_a, n_occ_b, n_vir_a, n_vir_b):
    print("NYI")
    exit()
