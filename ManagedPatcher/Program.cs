using Mono.Cecil;
using Mono.Cecil.Cil;
using System.Security.Cryptography;
using System.Text.Json;

if(args.Length!=3) throw new ArgumentException("source.dll target.dll verification.json");
var source=Path.GetFullPath(args[0]); var target=Path.GetFullPath(args[1]);
if(source==target) throw new InvalidOperationException("Never overwrite original assembly");
string Hash(string p)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))).ToLowerInvariant();
const string expected="f937abb2d67a4e41071cc1215f58eae4c04ff161406bdd295f43f3fe9862cdd0";
if(Hash(source)!=expected) throw new InvalidOperationException("Wrong source assembly hash");
IEnumerable<TypeDefinition> AllTypes(IEnumerable<TypeDefinition> types) {
    foreach(var t in types) {yield return t; foreach(var n in AllTypes(t.NestedTypes)) yield return n;}
}
string Fingerprint(MethodDefinition m) {
    if(!m.HasBody) return "NO_BODY";
    string Operand(object? o) => o switch {
        null => "", Instruction i => "@"+m.Body.Instructions.IndexOf(i),
        Instruction[] many => string.Join(",",many.Select(i=>"@"+m.Body.Instructions.IndexOf(i))),
        MethodReference x=>x.FullName, FieldReference x=>x.FullName, TypeReference x=>x.FullName,
        VariableDefinition x=>"V"+x.Index, ParameterDefinition x=>"P"+x.Index,
        string s=>"S:"+s, _=>o.ToString()??""
    };
    return string.Join("\n",m.Body.Instructions.Select(i=>i.OpCode.Name+" "+Operand(i.Operand)));
}
using var resolver=new DefaultAssemblyResolver();
resolver.AddSearchDirectory(Path.GetDirectoryName(source)!);
using var assembly=AssemblyDefinition.ReadAssembly(source,new ReaderParameters{InMemory=true,AssemblyResolver=resolver});
var module=assembly.MainModule;
var methods=AllTypes(module.Types).SelectMany(t=>t.Methods).ToList();
var before=methods.ToDictionary(m=>m.FullName,Fingerprint);
var references=module.AssemblyReferences.Select(r=>r.FullName).ToArray();
var screen=methods.Single(m=>m.Name=="MoveNext" && m.DeclaringType.FullName.StartsWith("IndexUIScreen/") && m.DeclaringType.FullName.Contains("loadSearch"));
var vowels=new Dictionary<string,string>{{"[Aa]","[AÁaá]"},{"[Ee]","[EÉeé]"},{"[Ii]","[IÍií]"},{"[Oo]","[OÓÖŐoóöő]"},{"[Uu]","[UÚÜŰuúüű]"}};
bool inEnglish=false; int replacements=0;
foreach(var i in screen.Body.Instructions) {
    if(i.OpCode!=OpCodes.Ldstr || i.Operand is not string s) continue;
    if(s=="en") {inEnglish=true; continue;}
    if(inEnglish && s=="fr") break;
    if(inEnglish && vowels.TryGetValue(s,out var hu)) {i.Operand=hu; replacements++;}
}
if(replacements!=5) throw new InvalidOperationException("Expected exactly five English vowel patterns");
// Display-only hardcoded UI literals outside uiTextHash (boundary findings M01/M02). Legal copyright text is kept.
var literalMap=new Dictionary<string,(string hu,int count)>{
    {"Version ",("Verzió ",2)}, {"\nVersion ",("\nVerzió ",1)},
    {"Type the notecard name here.",("Írja be a jegyzetkártya nevét.",1)}};
var literalHits=literalMap.Keys.ToDictionary(k=>k,_=>0); var literalMethods=new HashSet<string>();
foreach(var m in methods.Where(m=>m.HasBody)) foreach(var i in m.Body.Instructions) {
    if(i.OpCode==OpCodes.Ldstr && i.Operand is string s && literalMap.TryGetValue(s,out var t)) {i.Operand=t.hu; literalHits[s]++; literalMethods.Add(m.FullName);}
}
foreach(var p in literalMap) if(literalHits[p.Key]!=p.Value.count) throw new InvalidOperationException("Unexpected UI literal count: "+p.Key.Replace("\n","\\n")+" = "+literalHits[p.Key]);
var index=module.Types.Single(t=>t.Name=="IndexAndSearchFunctions");
var reader=index.Methods.Single(m=>m.Name=="readWords");
var comparer=module.Types.Single(t=>t.Name=="WordSortComparer");
var ctor=comparer.Methods.Single(m=>m.IsConstructor && !m.IsStatic && m.Parameters.Count==0);
// Reuse the original generic member-reference signature (IComparer<!0>),
// rather than baking IComparer<WordData> into a List<T> member reference.
var binary=index.Methods.Single(m=>m.Name=="SingleWordSearch").Body.Instructions
    .Select(i=>i.Operand).OfType<MethodReference>().Single(m=>m.Name=="BinarySearch");
var sort=new MethodReference("Sort",module.TypeSystem.Void,binary.DeclaringType){HasThis=true};
sort.Parameters.Add(new ParameterDefinition(binary.Parameters[1].ParameterType));
if(sort.Resolve() is not MethodDefinition resolvedSort || resolvedSort.Parameters.Count!=1)
    throw new InvalidOperationException("New generic Sort reference does not resolve against shipped mscorlib");
var rets=reader.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ret).ToList();
if(rets.Count!=1) throw new InvalidOperationException("Unexpected readWords control flow");
var il=reader.Body.GetILProcessor(); var ret=rets[0];
var first=il.Create(OpCodes.Ldarg_2);
il.InsertBefore(ret,first); il.InsertBefore(ret,il.Create(OpCodes.Newobj,ctor)); il.InsertBefore(ret,il.Create(OpCodes.Callvirt,sort));
foreach(var i in reader.Body.Instructions) {
    if(ReferenceEquals(i.Operand,ret)) i.Operand=first;
    else if(i.Operand is Instruction[] targets) for(int n=0;n<targets.Length;n++) if(ReferenceEquals(targets[n],ret)) targets[n]=first;
}
Directory.CreateDirectory(Path.GetDirectoryName(target)!);
assembly.Write(target);
using var check=AssemblyDefinition.ReadAssembly(target,new ReaderParameters{InMemory=true});
var after=AllTypes(check.MainModule.Types).SelectMany(t=>t.Methods).ToDictionary(m=>m.FullName,Fingerprint);
var changed=before.Where(p=>after[p.Key]!=p.Value).Select(p=>p.Key).Order().ToArray();
var expectedMethods=new[]{screen.FullName,reader.FullName}.Concat(literalMethods).Distinct().Order().ToArray();
if(!changed.SequenceEqual(expectedMethods) || before.Count!=after.Count) throw new InvalidOperationException("Unexpected method changes");
if(!references.SequenceEqual(check.MainModule.AssemblyReferences.Select(r=>r.FullName))) throw new InvalidOperationException("Runtime assembly references changed");
if(Hash(source)!=expected) throw new InvalidOperationException("Source was modified");
var verification=new {source_sha256=expected,target_sha256=Hash(target),changed_methods=changed,english_vowel_patterns=replacements,ui_literals_translated=literalHits.Values.Sum(),assembly_references_unchanged=true,method_count=before.Count,scope="English-slot Hungarian alphabet matching; runtime search-word sorting; 4 display-only UI literals (Version x3, notecard prompt). No activation or protection edits."};
File.WriteAllText(args[2],JsonSerializer.Serialize(verification,new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine(JsonSerializer.Serialize(verification));
