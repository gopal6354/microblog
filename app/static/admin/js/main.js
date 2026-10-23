const menuBtn = document.getElementById("menuBtn");

const sidebar = document.getElementById("sidebar");


if(menuBtn){

    menuBtn.addEventListener(
        "click",
        ()=>{

            sidebar.classList.toggle(
                "active"
            );

        }
    );

}
