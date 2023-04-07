upytl = {}

upytl.mount_component = function(id){
    var id = `#${id}`
    var c = Vue.extend({template: id})
    new c().$mount(id)
}